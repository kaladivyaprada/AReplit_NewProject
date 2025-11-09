import folium
from folium import plugins
import json
import os

class MapGenerator:
    """Generate interactive maps and visualizations"""
    
    def __init__(self):
        self.default_center = [20.5937, 78.9629]
        self.default_zoom = 5
    
    def create_base_map(self, center=None, zoom=None):
        """Create a base Folium map of India"""
        if not center:
            center = self.default_center
        if not zoom:
            zoom = self.default_zoom
        
        m = folium.Map(
            location=center,
            zoom_start=zoom,
            tiles='OpenStreetMap',
            control_scale=True
        )
        
        return m
    
    def add_crop_layer(self, map_obj, geometry, crop_data, crop_name, color):
        """Add a crop classification layer to the map"""
        if geometry['type'] == 'Polygon':
            folium.GeoJson(
                geometry,
                name=crop_name,
                style_function=lambda x: {
                    'fillColor': color,
                    'color': color,
                    'weight': 2,
                    'fillOpacity': 0.5
                },
                tooltip=f"{crop_name}: {crop_data.get('area_ha', 0):.2f} ha"
            ).add_to(map_obj)
        
        return map_obj
    
    def create_results_map(self, center, geometry, crop_distribution):
        """Create a map showing crop distribution results"""
        m = self.create_base_map(center=center, zoom=10)
        
        for crop_name, crop_info in crop_distribution.items():
            if crop_info['percentage'] > 5:
                self.add_crop_layer(
                    m, geometry, crop_info, crop_name, crop_info['color']
                )
        
        folium.LayerControl().add_to(m)
        
        return m
    
    def save_map_html(self, map_obj, filename='crop_map.html'):
        """Save map as HTML file"""
        output_dir = 'static/maps'
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        map_obj.save(filepath)
        return filepath
    
    def generate_geojson(self, geometry, properties):
        """Generate GeoJSON for download"""
        geojson = {
            'type': 'Feature',
            'geometry': geometry,
            'properties': properties
        }
        return geojson
    
    def export_to_csv(self, crop_distribution, filename='crop_analysis.csv'):
        """Export crop distribution to CSV"""
        import csv
        output_dir = 'static/exports'
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Crop Type', 'Area (Hectares)', 'Percentage', 'Confidence'])
            
            for crop_name, crop_info in crop_distribution.items():
                writer.writerow([
                    crop_name,
                    crop_info.get('area_ha', 0),
                    crop_info.get('percentage', 0),
                    crop_info.get('confidence', 0)
                ])
        
        return filepath
