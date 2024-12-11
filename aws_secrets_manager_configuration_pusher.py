import os
import boto3
import json
from botocore.exceptions import ClientError



# Function to read .env file
def read_env_file(file_path):
    env_vars = {}
    try:
        with open(file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip().strip("'").strip('"')
    except FileNotFoundError:
        print(f"Error: .env file not found at {file_path}")
        return None
    except Exception as e:
        print(f"Error reading .env file: {str(e)}")
        return None
    return env_vars

# Function to update or create a secret
def update_or_create_secret(secrets_manager, secret_name, secret_string):
    try:
        secrets_manager.update_secret(
            SecretId=secret_name,
            SecretString=secret_string
        )
        print(f"Secret '{secret_name}' updated successfully.")
    except secrets_manager.exceptions.ResourceNotFoundException:
        secrets_manager.create_secret(
            Name=secret_name,
            Description='Environment variables from .env file and existing secret',
            SecretString=secret_string
        )
        print(f"Secret '{secret_name}' created successfully.")

# Function to merge and copy secret
def merge_and_copy_secret(env_vars, source_secret_name, destination_secret_name, source_region='us-east-2', destination_region='us-east-2'):
    source_secrets_manager = boto3.client('secretsmanager', region_name=source_region)
    destination_secrets_manager = boto3.client('secretsmanager', region_name=destination_region)

    try:
        # Try to get the secret value from the source
        try:
            response = source_secrets_manager.get_secret_value(SecretId=source_secret_name)
            source_secret_string = response['SecretString']
            source_dict = json.loads(source_secret_string)
            print(f"Source secret '{source_secret_name}' found and loaded.")
            
            # Merge env_vars with source secret
            merged_dict = {**source_dict, **env_vars}  # env_vars take precedence
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"Source secret '{source_secret_name}' not found. Using only env_vars.")
                merged_dict = env_vars
            else:
                raise

        merged_secret_string = json.dumps(merged_dict)

        # Update or create the secret in the destination
        update_or_create_secret(destination_secrets_manager, destination_secret_name, merged_secret_string)
        print(f"Secret {'merged and ' if 'source_dict' in locals() else ''}copied to '{destination_secret_name}' successfully.")
    except Exception as e:
        print(f"Error in merge_and_copy_secret: {str(e)}")

# Get the current script's directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Navigate up three levels to get to the root path
ROOT_PATH = os.path.abspath(os.path.join(CURRENT_DIR))
CONFIG_FILE_NAME = "any.env"
ENV_FILE_PATH = os.path.join(ROOT_PATH,CONFIG_FILE_NAME)

print(f"Looking for .env file at: {ENV_FILE_PATH}")

# Read the .env file
env_vars = read_env_file(ENV_FILE_PATH)

if env_vars is None:
    print("Failed to read .env file. Exiting.")
    exit(1)

print("Loaded environment variables:")
print(json.dumps(env_vars, indent=2))

# Name of the source and destination secrets in AWS Secrets Manager
source_secret_name = 'any'
destination_secret_name = 'any'

# Merge and copy the secret
merge_and_copy_secret(env_vars, source_secret_name, destination_secret_name)
