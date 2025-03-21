import firebase_admin
from firebase_admin import credentials, storage, firestore
import uuid
import io
import os
from PIL import Image  # Assuming you're using PIL for image manipulation

def initialize_firebase(service_account_path):
    """Initializes Firebase Admin SDK."""
    try:
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred, {
            'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET')  # Replace with your bucket
        })
        return storage.bucket(), firestore.client()
    except Exception as e:
        print(f"Error initializing Firebase: {e}")
        return None, None

def upload_image_to_firebase(bucket, image_data, image_format="PNG"):
    """Uploads an image to Firebase Storage and returns the URL."""
    try:
        blob_name = f"images/{uuid.uuid4()}.{image_format.lower()}" # create unique file name
        blob = bucket.blob(blob_name)

        if isinstance(image_data, bytes): # handle bytes data
            blob.upload_from_string(image_data, content_type=f'image/{image_format.lower()}')

        elif isinstance(image_data, Image.Image): # handle PIL image
            img_byte_arr = io.BytesIO()
            image_data.save(img_byte_arr, format=image_format)
            img_byte_arr = img_byte_arr.getvalue()
            blob.upload_from_string(img_byte_arr, content_type=f'image/{image_format.lower()}')

        else:
            raise ValueError("image_data must be bytes or a PIL Image object")

        blob.make_public()
        image_url = blob.public_url

        return image_url

    except Exception as e:
        print(f"Error uploading image: {e}")
        return None

def store_image_url_in_firestore(db, image_url, collection_name="images", document_id=None, additional_data={}):
    """Stores the image URL in Firestore."""
    try:
        if document_id is None:
          doc_ref = db.collection(collection_name).document()
        else:
          doc_ref = db.collection(collection_name).document(document_id)

        doc_data = {"image_url": image_url, **additional_data} #merge additional data
        doc_ref.set(doc_data)
        return doc_ref.id # Return the document ID
    except Exception as e:
        print(f"Error storing URL in Firestore: {e}")
        return None

def generate_and_store_image(service_account_path, image_generation_function, image_format="PNG", firestore_collection="images", firestore_document_id=None, firestore_additional_data={}):
    """Generates an image, uploads it to Firebase, and stores the URL in Firestore."""
    bucket, db = initialize_firebase(service_account_path)

    if not bucket or not db:
        return None, None # Return None if initialization fails

    try:
        image_data = image_generation_function() # Generate the image data (bytes or PIL Image)
        image_url = upload_image_to_firebase(bucket, image_data, image_format)

        if image_url:
            doc_id = store_image_url_in_firestore(db, image_url, firestore_collection, firestore_document_id, firestore_additional_data)
            return image_url, doc_id
        else:
            return None, None

    except Exception as e:
        print(f"Error in generate_and_store_image: {e}")
        return None, None

# Example Usage:
def my_image_generator():
    """Example image generation function (replace with your logic)."""
    # Example using PIL (Pillow)
    img = Image.new('RGB', (256, 256), color = 'red')
    return img

service_account_file = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'service-account.json') # Replace with your service account key path

image_url, document_id = generate_and_store_image(
    service_account_file,
    my_image_generator,
    image_format="PNG",
    firestore_collection="my_images",
    firestore_additional_data = {"some_metadata":"example_value"}
)

if image_url:
    print(f"Image uploaded successfully. URL: {image_url}, Document ID: {document_id}")
else:
    print("Image upload failed.")

#_____________________________________________________________________________
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