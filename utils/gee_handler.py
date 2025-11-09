import os
import json
import ee
from datetime import datetime, timedelta

class GEEHandler:
    """Handler for Google Earth Engine operations"""
    
    def __init__(self):
        self.initialized = False
        self.initialize_gee()
    
    def initialize_gee(self):
        """Initialize Google Earth Engine with service account or default credentials"""
        try:
            service_account = os.getenv('GEE_SERVICE_ACCOUNT')
            private_key = os.getenv('GEE_PRIVATE_KEY')
            
            if service_account and private_key:
                credentials = ee.ServiceAccountCredentials(service_account, key_data=private_key)
                ee.Initialize(credentials)
                self.initialized = True
                print("✓ GEE initialized with service account")
            else:
                ee.Initialize()
                self.initialized = True
                print("✓ GEE initialized with default credentials")
        except Exception as e:
            print(f"⚠ GEE initialization failed: {e}")
            print("  Demo mode: Will use simulated data")
            self.initialized = False
    
    def get_sentinel2_ndvi(self, geometry, start_date=None, end_date=None):
        """
        Fetch Sentinel-2 NDVI data for a given geometry
        
        Args:
            geometry: dict with 'type' and 'coordinates' (GeoJSON format)
            start_date: str, format 'YYYY-MM-DD'
            end_date: str, format 'YYYY-MM-DD'
        
        Returns:
            dict with NDVI statistics and time series
        """
        if not self.initialized:
            return self._generate_demo_ndvi_data(geometry)
        
        try:
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            
            ee_geometry = self._convert_to_ee_geometry(geometry)
            
            collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                         .filterBounds(ee_geometry)
                         .filterDate(start_date, end_date)
                         .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)))
            
            def add_ndvi(image):
                ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
                return image.addBands(ndvi)
            
            collection_with_ndvi = collection.map(add_ndvi)
            
            ndvi_median = collection_with_ndvi.select('NDVI').median()
            ndvi_25th = collection_with_ndvi.select('NDVI').reduce(ee.Reducer.percentile([25]))
            ndvi_75th = collection_with_ndvi.select('NDVI').reduce(ee.Reducer.percentile([75]))
            
            stats_median = ndvi_median.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=ee_geometry,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            
            stats_25th = ndvi_25th.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=ee_geometry,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            
            stats_75th = ndvi_75th.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=ee_geometry,
                scale=30,
                maxPixels=1e9
            ).getInfo()
            
            mean_ndvi = stats_median.get('NDVI', 0.5)
            percentile_25 = stats_25th.get('NDVI_p25', stats_25th.get('NDVI', mean_ndvi - 0.15))
            percentile_75 = stats_75th.get('NDVI_p75', stats_75th.get('NDVI', mean_ndvi + 0.15))
            
            return {
                'success': True,
                'mean_ndvi': mean_ndvi,
                'percentile_25': percentile_25,
                'percentile_50': mean_ndvi,
                'percentile_75': percentile_75,
                'image_count': collection.size().getInfo(),
                'start_date': start_date,
                'end_date': end_date
            }
        except Exception as e:
            print(f"Error fetching GEE data: {e}")
            return self._generate_demo_ndvi_data(geometry)
    
    def _convert_to_ee_geometry(self, geometry):
        """Convert GeoJSON geometry to EE geometry"""
        if geometry['type'] == 'Polygon':
            coords = geometry['coordinates'][0]
            return ee.Geometry.Polygon(coords)
        elif geometry['type'] == 'Point':
            coords = geometry['coordinates']
            return ee.Geometry.Point(coords)
        else:
            return ee.Geometry.Rectangle(geometry.get('bbox', [0, 0, 1, 1]))
    
    def _generate_demo_ndvi_data(self, geometry):
        """Generate simulated NDVI data for demo purposes"""
        import random
        random.seed(hash(str(geometry)) % 1000)
        
        base_ndvi = random.uniform(0.4, 0.7)
        
        return {
            'success': True,
            'demo_mode': True,
            'mean_ndvi': base_ndvi,
            'percentile_25': max(0.1, base_ndvi - 0.15),
            'percentile_50': base_ndvi,
            'percentile_75': min(0.9, base_ndvi + 0.15),
            'image_count': random.randint(5, 15),
            'start_date': (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
            'end_date': datetime.now().strftime('%Y-%m-%d')
        }
    
    def get_ndvi_features(self, geometry, start_date=None, end_date=None):
        """Extract NDVI-based features for ML model"""
        ndvi_data = self.get_sentinel2_ndvi(geometry, start_date, end_date)
        
        features = [
            ndvi_data['mean_ndvi'],
            ndvi_data['percentile_25'],
            ndvi_data['percentile_50'],
            ndvi_data['percentile_75'],
            ndvi_data['percentile_75'] - ndvi_data['percentile_25'],
            ndvi_data.get('image_count', 10) / 10.0
        ]
        
        return features, ndvi_data
