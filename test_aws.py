import os
import boto3
from dotenv import load_dotenv

def test_aws_connection():
    # Load environment variables
    load_dotenv()
    
    # Print environment variables (without showing full secret key)
    print("Checking environment variables:")
    print(f"AWS_ACCESS_KEY_ID: {os.getenv('AWS_ACCESS_KEY_ID')[:5]}...")
    print(f"AWS_SECRET_ACCESS_KEY: {'*' * 10}...")
    print(f"AWS_REGION: {os.getenv('AWS_REGION')}")
    
    try:
        # Initialize S3 client
        s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-2')
        )
        
        # Try to list buckets (this will verify credentials)
        print("\nTesting AWS connection...")
        response = s3.list_buckets()
        
        # Print bucket names
        print("\nAvailable S3 buckets:")
        for bucket in response['Buckets']:
            print(f"- {bucket['Name']}")
            
        # Try to list objects in the compoundfoundry bucket
        print("\nTesting access to compoundfoundry bucket...")
        try:
            objects = s3.list_objects_v2(Bucket='compoundfoundry', MaxKeys=5)
            print("Successfully accessed compoundfoundry bucket!")
            if 'Contents' in objects:
                print("\nFirst 5 objects in bucket:")
                for obj in objects['Contents']:
                    print(f"- {obj['Key']}")
            else:
                print("Bucket is empty or no objects found")
        except Exception as e:
            print(f"Error accessing compoundfoundry bucket: {str(e)}")
            
        return True
        
    except Exception as e:
        print(f"\nError connecting to AWS: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting AWS connection test...\n")
    success = test_aws_connection()
    print("\nTest completed:", "SUCCESS" if success else "FAILED") 