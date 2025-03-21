import firebase_admin
from firebase_admin import credentials, storage, firestore
import uuid
import io
import os
from PIL import Image  # Assuming you're using PIL for image manipulation


import os
from app.services.logger import setup_logger

logger = setup_logger(__name__)

class FirebaseManager:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not FirebaseManager._initialized:
            try:
                # Initialize Firebase if not already initialized
                if not firebase_admin._apps:
                    cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred, {
                        'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET')
                    })
                self.bucket = storage.bucket()
                logger.info(f"Firebase initialized with bucket: {self.bucket}")
                FirebaseManager._initialized = True
                logger.info("Firebase initialized successfully")
            except Exception as e:
                logger.error(f"Firebase initialization failed: {str(e)}")
                raise
    
    def upload_image(self, image_data, filename=None):
        """Upload image to Firebase Storage and return public URL"""
        try:
            if not filename:
                filename = f"images/{uuid.uuid4()}.png"

            # Ensure image_data is bytes
            if not isinstance(image_data, bytes):
                raise ValueError(f"Image data must be bytes, got {type(image_data)}")
            
            blob = self.bucket.blob(filename)
            blob.upload_from_string(image_data, content_type="image/png")
            blob.make_public()
            
            return blob.public_url
        except Exception as e:
            logger.error(f"Failed to upload image to Firebase: {str(e)}")
            return None