from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import json
import os
from datetime import datetime
from utils.gee_handler import GEEHandler
from utils.model_predictor import CropPredictor
from utils.map_generator import MapGenerator

app = Flask(__name__)
CORS(app)

gee_handler = GEEHandler()
crop_predictor = CropPredictor()
map_generator = MapGenerator()

with open('data/regions.json', 'r') as f:
    regions_data = json.load(f)

with open('data/crop_data.json', 'r') as f:
    crop_data = json.load(f)

@app.route('/')
def index():
    """Render main application page"""
    return render_template('index.html')

@app.route('/api/regions', methods=['GET'])
def get_regions():
    """Get Indian administrative regions data"""
    return jsonify(regions_data)

@app.route('/api/crop-types', methods=['GET'])
def get_crop_types():
    """Get crop types and metadata"""
    return jsonify(crop_data)

@app.route('/api/analyze', methods=['POST'])
def analyze_region():
    """
    Analyze a selected region for crop classification
    
    Expected JSON payload:
    {
        "geometry": {...},  # GeoJSON geometry
        "center": [lat, lon],
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD",
        "region_name": "Region Name"
    }
    """
    try:
        data = request.get_json()
        
        geometry = data.get('geometry')
        center = data.get('center', [20.5937, 78.9629])
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        region_name = data.get('region_name', 'Selected Region')
        
        if not geometry:
            return jsonify({'error': 'No geometry provided'}), 400
        
        print(f"Analyzing region: {region_name}")
        
        features, ndvi_data = gee_handler.get_ndvi_features(geometry, start_date, end_date)
        
        prediction = crop_predictor.predict_crop(features)
        
        area_distribution = crop_predictor.predict_area_distribution(geometry, ndvi_data)
        
        result = {
            'success': True,
            'region_name': region_name,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ndvi_data': ndvi_data,
            'dominant_crop': prediction['predicted_crop'],
            'confidence': prediction['confidence'],
            'total_area_ha': area_distribution['total_area_ha'],
            'crop_distribution': area_distribution['crop_distribution'],
            'all_probabilities': prediction['all_probabilities'],
            'center': center,
            'demo_mode': ndvi_data.get('demo_mode', False) or prediction.get('demo_mode', False)
        }
        
        if result['demo_mode']:
            result['warning'] = 'Demo mode: Using simulated data. Configure GEE credentials for real satellite analysis.'
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error in analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/csv', methods=['POST'])
def export_csv():
    """Export analysis results to CSV"""
    try:
        data = request.get_json()
        crop_distribution = data.get('crop_distribution', {})
        region_name = data.get('region_name', 'analysis')
        
        filename = f"{region_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = map_generator.export_to_csv(crop_distribution, filename)
        
        return send_file(filepath, as_attachment=True, download_name=filename)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/geojson', methods=['POST'])
def export_geojson():
    """Export analysis results to GeoJSON"""
    try:
        data = request.get_json()
        geometry = data.get('geometry')
        properties = data.get('properties', {})
        
        geojson = map_generator.generate_geojson(geometry, properties)
        
        return jsonify(geojson)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'gee_initialized': gee_handler.initialized,
        'model_loaded': crop_predictor.model is not None,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🌾 CROP CLASSIFICATION SYSTEM FOR INDIA")
    print("="*60)
    print(f"✓ Flask server starting...")
    print(f"✓ GEE Handler: {'Initialized' if gee_handler.initialized else 'Demo Mode'}")
    print(f"✓ ML Model: {'Loaded' if crop_predictor.model else 'Not Available'}")
    print(f"✓ Regions loaded: {len(regions_data['states'])} states")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
