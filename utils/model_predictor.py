import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import json

class CropPredictor:
    """Machine Learning model for crop classification"""
    
    def __init__(self, model_path='models/crop_classifier.pkl'):
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.crop_labels = ['Paddy/Rice', 'Millet/Pulses', 'Cash Crops', 'Fallow/Barren']
        self.crop_colors = ['#2ecc71', '#f39c12', '#8b4513', '#95a5a6']
        self.load_or_create_model()
    
    def load_or_create_model(self):
        """Load existing model or create a new pre-trained one"""
        if os.path.exists(self.model_path):
            try:
                saved_data = joblib.load(self.model_path)
                self.model = saved_data['model']
                self.scaler = saved_data['scaler']
                print("✓ Loaded pre-trained crop classification model")
            except Exception as e:
                print(f"⚠ Error loading model: {e}, creating new one")
                self.create_pretrained_model()
        else:
            self.create_pretrained_model()
    
    def create_pretrained_model(self):
        """Create and save a pre-trained Random Forest model with synthetic data"""
        print("Creating pre-trained crop classification model...")
        
        np.random.seed(42)
        n_samples = 1000
        
        X_train = []
        y_train = []
        
        for crop_id in range(4):
            for _ in range(n_samples // 4):
                if crop_id == 0:
                    ndvi_mean = np.random.uniform(0.6, 0.85)
                    ndvi_25 = np.random.uniform(0.55, ndvi_mean)
                    ndvi_50 = ndvi_mean
                    ndvi_75 = np.random.uniform(ndvi_mean, 0.9)
                elif crop_id == 1:
                    ndvi_mean = np.random.uniform(0.4, 0.6)
                    ndvi_25 = np.random.uniform(0.35, ndvi_mean)
                    ndvi_50 = ndvi_mean
                    ndvi_75 = np.random.uniform(ndvi_mean, 0.65)
                elif crop_id == 2:
                    ndvi_mean = np.random.uniform(0.5, 0.7)
                    ndvi_25 = np.random.uniform(0.45, ndvi_mean)
                    ndvi_50 = ndvi_mean
                    ndvi_75 = np.random.uniform(ndvi_mean, 0.75)
                else:
                    ndvi_mean = np.random.uniform(0.1, 0.35)
                    ndvi_25 = np.random.uniform(0.05, ndvi_mean)
                    ndvi_50 = ndvi_mean
                    ndvi_75 = np.random.uniform(ndvi_mean, 0.4)
                
                ndvi_range = ndvi_75 - ndvi_25
                image_count = np.random.uniform(0.5, 1.5)
                
                features = [ndvi_mean, ndvi_25, ndvi_50, ndvi_75, ndvi_range, image_count]
                X_train.append(features)
                y_train.append(crop_id)
        
        X_train = np.array(X_train)
        y_train = np.array(y_train)
        
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42
        )
        self.model.fit(X_train_scaled, y_train)
        
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({'model': self.model, 'scaler': self.scaler}, self.model_path)
        print(f"✓ Created and saved model to {self.model_path}")
    
    def predict_crop(self, features):
        """
        Predict crop type from NDVI features
        
        Args:
            features: list of NDVI-based features
        
        Returns:
            dict with prediction results
        """
        if self.model is None:
            return self._get_demo_prediction()
        
        try:
            features_array = np.array(features).reshape(1, -1)
            features_scaled = self.scaler.transform(features_array)
            
            prediction = self.model.predict(features_scaled)[0]
            probabilities = self.model.predict_proba(features_scaled)[0]
            
            crop_distributions = {}
            for i, crop in enumerate(self.crop_labels):
                crop_distributions[crop] = {
                    'probability': float(probabilities[i]),
                    'color': self.crop_colors[i]
                }
            
            return {
                'predicted_crop': self.crop_labels[prediction],
                'crop_id': int(prediction),
                'confidence': float(probabilities[prediction]),
                'color': self.crop_colors[prediction],
                'all_probabilities': crop_distributions,
                'features': features
            }
        except Exception as e:
            print(f"Prediction error: {e}")
            return self._get_demo_prediction()
    
    def _get_demo_prediction(self):
        """Generate demo prediction when model is unavailable"""
        return {
            'predicted_crop': 'Paddy/Rice',
            'crop_id': 0,
            'confidence': 0.85,
            'color': '#2ecc71',
            'all_probabilities': {
                'Paddy/Rice': {'probability': 0.85, 'color': '#2ecc71'},
                'Millet/Pulses': {'probability': 0.10, 'color': '#f39c12'},
                'Cash Crops': {'probability': 0.03, 'color': '#8b4513'},
                'Fallow/Barren': {'probability': 0.02, 'color': '#95a5a6'}
            },
            'demo_mode': True
        }
    
    def predict_area_distribution(self, geometry, ndvi_data):
        """
        Simulate crop distribution across an area
        Returns area statistics for different crop types
        """
        import random
        random.seed(hash(str(geometry)) % 1000)
        
        mean_ndvi = ndvi_data.get('mean_ndvi', 0.5)
        
        if mean_ndvi > 0.65:
            dominant_crop = 0
            distribution = [0.55, 0.25, 0.15, 0.05]
        elif mean_ndvi > 0.5:
            dominant_crop = 2
            distribution = [0.20, 0.30, 0.40, 0.10]
        elif mean_ndvi > 0.35:
            dominant_crop = 1
            distribution = [0.15, 0.50, 0.25, 0.10]
        else:
            dominant_crop = 3
            distribution = [0.05, 0.15, 0.10, 0.70]
        
        variation = [random.uniform(-0.05, 0.05) for _ in range(4)]
        distribution = [max(0.01, d + v) for d, v in zip(distribution, variation)]
        
        total = sum(distribution)
        distribution = [d / total for d in distribution]
        
        area_estimate = random.uniform(10000, 50000)
        
        result = {
            'total_area_ha': round(area_estimate, 2),
            'dominant_crop': self.crop_labels[dominant_crop],
            'crop_distribution': {}
        }
        
        for i, crop in enumerate(self.crop_labels):
            result['crop_distribution'][crop] = {
                'area_ha': round(distribution[i] * area_estimate, 2),
                'percentage': round(distribution[i] * 100, 2),
                'color': self.crop_colors[i],
                'confidence': round(random.uniform(0.75, 0.95), 2)
            }
        
        return result
