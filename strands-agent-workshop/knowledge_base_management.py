import boto3
import json
import time
import os

def create_knowledge_base_with_s3_vectors(topic_base: str, files: list[(str,str)], region="us-east-1"):
    """Create Bedrock Knowledge Base with S3 Vectors - clean and simple"""
    sts = boto3.client('sts', region_name=region)
    account_id = sts.get_caller_identity()['Account']
    topic = topic_base + '-' + account_id
    bucket_name = topic
    kb_name = topic + '-kb'
    vector_bucket_name = topic + '-vectors' 
    role_name = f"{topic}-knowledge-base-access-role"
    vector_index_name = f"{topic}-knowledge-base-index"
    # Initialize clients
    bedrock_agent = boto3.client('bedrock-agent', region_name=region)
    s3 = boto3.client('s3', region_name=region)
    s3vectors = boto3.client('s3vectors', region_name=region)
    iam = boto3.client('iam', region_name=region)
    #kb name = bucket name
    clean_up_knowledgebase(bedrock_agent, kb_name)
    create_s3_bucket(s3, bucket_name, region)
    for file in files:
        source, target = file
        upload_file(s3, bucket_name, source, target)
    vector_index_arn = create_s3_vector_bucket(s3vectors, region, account_id, vector_bucket_name, vector_index_name)
    role_arn = create_bedrock_iam(iam, role_name, bucket_name, region)
    kb_id = create_bedrock_knowledge_base(bedrock_agent, kb_name, region, role_arn, vector_index_arn)
    add_data_source_to_knowledge_base(bedrock_agent, kb_name, bucket_name, kb_id)
    print(f"🚀 Creating Knowledge Base: {kb_name}")
    print(f"📊 Using S3 Vectors for vector storage")
    
    print(f"\n🎉 Success! Knowledge Base created with S3 Vectors")
    print(f"📋 Knowledge Base ID: {kb_id}")
    print(f"🎯 Vector Bucket: {vector_bucket_name}")
    print(f"📍 Vector Index: {vector_index_name}")
    print(f"🔑 IAM Role: {role_name}")
    return kb_id
    
def update_knowledge_base_with_s3_vectors(topic_base: str, files: list[(str,str)], kb_id, region="us-east-1"):
    """Create Bedrock Knowledge Base with S3 Vectors - clean and simple"""
    sts = boto3.client('sts', region_name=region)
    account_id = sts.get_caller_identity()['Account']
    topic = topic_base + '-' + account_id
    bucket_name = topic
    kb_name = topic + '-kb'
    vector_bucket_name = topic + '-vectors' 
    role_name = f"{topic}-knowledge-base-access-role"
    vector_index_name = f"{topic}-knowledge-base-index"
    # Initialize clients
    bedrock_agent = boto3.client('bedrock-agent', region_name=region)
    s3 = boto3.client('s3', region_name=region)
    #kb name = bucket name
    for file in files:
        source, target = file
        upload_file(s3, bucket_name, source, target)
    update_data_source(bedrock_agent, kb_name, bucket_name, kb_id)
    
    print(f"\n🎉 Success! Knowledge Base updated knowledge base with S3 Vectors")
    print(f"📋 Knowledge Base ID: {kb_id}")
    print(f"🎯 Vector Bucket: {vector_bucket_name}")
    print(f"📍 Vector Index: {vector_index_name}")
    print(f"🔑 IAM Role: {role_name}")
    return kb_id

def retrieve_knowledge_base(topic_base:str, region= "us-east-1"):
    sts = boto3.client('sts', region_name=region)
    account_id = sts.get_caller_identity()['Account']
    topic = topic_base + '-' + account_id
    kb_name = topic + '-kb'
    bedrock_agent = boto3.client('bedrock-agent', region_name=region)
    try:
        kbs = bedrock_agent.list_knowledge_bases()
        for kb in kbs.get('knowledgeBaseSummaries', []):
            if kb['name'] == kb_name:
                return kb['knowledgeBaseId']
    except:
        pass

# 1. Cleanup existing KB
def clean_up_knowledgebase(bedrock_agent, kb_name):
    try:
        kbs = bedrock_agent.list_knowledge_bases()
        for kb in kbs.get('knowledgeBaseSummaries', []):
            if kb['name'] == kb_name:
                print(f"🗑️  Deleting existing KB: {kb_name}")
                bedrock_agent.delete_knowledge_base(knowledgeBaseId=kb['knowledgeBaseId'])
                time.sleep(10)  # Wait for deletion
                break
    except:
        pass

# 2. Create S3 bucket for documents and upload
def create_s3_bucket(s3, bucket_name, region):
    print(f"📦 Creating S3 bucket for documents: {bucket_name}")
    try:
        if region == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        print(f"✅ Created S3 bucket: {bucket_name}")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"✅ S3 bucket already exists: {bucket_name}")
    except Exception as e:
        print(f"❌ Error creating bucket: {e}")
        raise
    
# Upload file to S3
def upload_file(s3, bucket_name, source_file, target_file):
    s3.upload_file(source_file, bucket_name, target_file)
    print(f"✅ Uploaded to S3: {bucket_name}")
    
# 3. Create S3 Vector Bucket
def create_s3_vector_bucket(s3vectors_client, region, account_id, vector_bucket_name, vector_index_name):
    print(f"🎯 Creating S3 vector bucket: {vector_bucket_name}")
    try:
        # Delete existing vector bucket if it exists
        try:
            s3vectors_client.delete_vector_bucket(
                vectorBucketName=vector_bucket_name
            )
            print(f"🗑️  Deleted existing vector bucket")
            time.sleep(15)  # Wait for deletion to complete
        except:
            pass
        
        # Create new vector bucket
        vector_bucket_response = s3vectors_client.create_vector_bucket(
            vectorBucketName=vector_bucket_name,
            encryptionConfiguration={
                'sseType': 'AES256'
            }
        )
        # Construct the ARN  
        vector_bucket_arn = f"arn:aws:s3vectors:{region}:{account_id}:bucket/{vector_bucket_name}"
        print(f"✅ Created S3 vector bucket: {vector_bucket_name}")
        
        # Wait for vector bucket to be active
        print("⏳ Waiting for vector bucket to be active...")
        time.sleep(5)
        
    except Exception as e:
        if "already exists" in str(e):
            vector_bucket_arn = f"arn:aws:s3vectors:{region}:{account_id}:bucket/{vector_bucket_name}"
            print(f"✅ Using existing vector bucket: {vector_bucket_name}")
        else:
            print(f"❌ Error creating vector bucket: {e}")
            raise
    # 4. Create Vector Index
    print(f"📍 Creating vector index: {vector_index_name}")
    try:
        # Delete existing index if it exists
        try:
            s3vectors_client.delete_index(
                vectorBucketName=vector_bucket_name,
                indexName=vector_index_name
            )
            print(f"🗑️  Deleted existing vector index")
            time.sleep(10)  # Wait for deletion
        except:
            pass
        
        # Create vector index with proper configuration for Bedrock
        vector_index_response = s3vectors_client.create_index(
            vectorBucketName=vector_bucket_name,  # Use bucket name, not ARN
            indexName=vector_index_name,  # Correct parameter name
            dataType='float32',  # Required parameter
            dimension=1024,  # Amazon Titan Text Embeddings V2 dimensions (singular, not plural)
            distanceMetric='cosine',  # Lowercase, recommended for Titan embeddings
            metadataConfiguration={  # Correct structure
                'nonFilterableMetadataKeys': ['AMAZON_BEDROCK_TEXT']  # Required for large text chunks
            }
        )
        vector_index_arn = f"arn:aws:s3vectors:{region}:{account_id}:bucket/{vector_bucket_name}/index/{vector_index_name}"
        print(f"✅ Created vector index: {vector_index_name}")
        
        # Wait for index to be ready
        print("⏳ Waiting for vector index to be ready...")
        time.sleep(10)
        return vector_index_arn
        
    except Exception as e:
        if "already exists" in str(e):
            vector_index_arn = f"arn:aws:s3vectors:{region}:{account_id}:bucket/{vector_bucket_name}/index/{vector_index_name}"
            print(f"✅ Using existing vector index: {vector_index_name}")
        else:
            print(f"❌ Error creating vector index: {e}")
            raise

def create_bedrock_iam(iam_client, role_name, bucket_name, region):
    # 5. Create IAM role for Bedrock Knowledge Base
    print(f"🔑 Creating IAM role for Bedrock: {role_name}")
    
    # Trust policy - allows bedrock.amazonaws.com to assume this role
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    # Permissions policy - what the role can do
    permissions_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3vectors:*"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    f"arn:aws:s3:::{bucket_name}",
                    f"arn:aws:s3:::{bucket_name}/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel"
                ],
                "Resource": f"arn:aws:bedrock:{region}::foundation-model/amazon.titan-embed-text-v2:0"
            }
        ]
    }
    
    try:
        # Try to create the role
        role_response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description=f"Role for Bedrock Knowledge Base {bucket_name}"
        )
        role_arn = role_response['Role']['Arn']
        print(f"✅ Created IAM role: {role_name}")
        
        # Attach the permissions policy
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=f"{role_name}-permissions",
            PolicyDocument=json.dumps(permissions_policy)
        )
        print(f"✅ Attached permissions policy")
        
        # Wait for the role to propagate
        print("⏳ Waiting for IAM role to propagate...")
        time.sleep(15)  # Increased wait time
        return role_arn
        
    except iam_client.exceptions.EntityAlreadyExistsException:
        # Role already exists, get its ARN and update the policy
        role_arn = iam_client.get_role(RoleName=role_name)['Role']['Arn']
        print(f"✅ Using existing IAM role: {role_name}")
        
        # Update the permissions policy in case resources changed
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=f"{role_name}-permissions", 
            PolicyDocument=json.dumps(permissions_policy)
        )
        print(f"✅ Updated permissions policy")
        return role_arn
    except Exception as e:
        print(f"❌ Error creating/updating IAM role: {e}")
        raise

def create_bedrock_knowledge_base(bedrock_agent_client, kb_name, region, role_arn, vector_index_arn):
    # 6. Create Knowledge Base with S3 Vectors
    print("📝 Creating Knowledge Base with S3 Vectors...")
    try:
        kb_response = bedrock_agent_client.create_knowledge_base(
            name=kb_name,
            description=f"Knowledge base: {kb_name} using S3 Vectors",
            roleArn=role_arn,
            knowledgeBaseConfiguration={
                'type': 'VECTOR',
                'vectorKnowledgeBaseConfiguration': {
                    'embeddingModelArn': f'arn:aws:bedrock:{region}::foundation-model/amazon.titan-embed-text-v2:0',
                    'embeddingModelConfiguration': {
                        'bedrockEmbeddingModelConfiguration': {
                            'dimensions': 1024
                        }
                    }
                }
            },
            storageConfiguration={
                'type': 'S3_VECTORS',
                's3VectorsConfiguration': {
                    'indexArn': vector_index_arn
                }
            }
        )
        
        kb_id = kb_response['knowledgeBase']['knowledgeBaseId']
        print(f"✅ Knowledge Base created: {kb_id}")
        
    except Exception as e:
        print(f"❌ Error creating Knowledge Base: {e}")
        raise
    
    # Wait for KB to be active
    print("⏳ Waiting for Knowledge Base to be active...")
    while True:
        kb_status = bedrock_agent_client.get_knowledge_base(knowledgeBaseId=kb_id)
        status = kb_status['knowledgeBase']['status']
        if status == 'ACTIVE':
            print("✅ Knowledge Base is active")
            break
        elif status == 'FAILED':
            raise Exception(f"Knowledge Base creation failed: {kb_status}")
        time.sleep(10)
    return kb_id

def add_data_source_to_knowledge_base(bedrock_agent, kb_name, bucket_name, kb_id):
    # 7. Create data source and ingest
    print("📊 Creating data source...")
    ds_response = bedrock_agent.create_data_source(
        knowledgeBaseId=kb_id,
        name=f"{kb_name}-datasource",
        description="S3 data source",
        dataSourceConfiguration={
            'type': 'S3',
            's3Configuration': {
                'bucketArn': f'arn:aws:s3:::{bucket_name}' # Only process our specific file
            }
        }
    )
    
    ds_id = ds_response['dataSource']['dataSourceId']
    print(f"✅ Data source created: {ds_id}")
    
    # 8. Start ingestion job
    print("🔄 Starting ingestion job...")
    job_response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=kb_id,
        dataSourceId=ds_id
    )
    job_id = job_response['ingestionJob']['ingestionJobId']
    
    # Wait for ingestion to complete
    print("⏳ Waiting for ingestion to complete...")
    while True:
        job_status = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id,
            ingestionJobId=job_id
        )
        status = job_status['ingestionJob']['status']
        
        if status == 'COMPLETE':
            print("✅ Ingestion completed successfully")
            break
        elif status == 'FAILED':
            failure_reasons = job_status['ingestionJob'].get('failureReasons', ['Unknown error'])
            raise Exception(f"Ingestion failed: {failure_reasons}")
        elif status in ['IN_PROGRESS', 'STARTING']:
            print(f"⏳ Ingestion status: {status}")
            time.sleep(15)
        else:
            print(f"❓ Unexpected status: {status}")
            time.sleep(10)

def update_data_source(bedrock_agent, kb_name, bucket_name, kb_id):
    # 8. Update data source and ingest
    print("📊 Updating data source...")
    response = bedrock_agent.list_data_sources(knowledgeBaseId=kb_id)
    ds_name = f"{kb_name}-datasource"
    ds_id = None
    for ds in response.get('dataSourceSummaries', []):
            if ds['name'] == ds_name:
                ds_id = ds['dataSourceId']

    if ds_id is None:
        print(f"✅ Data source Not Found: {ds_id}")
        return kb_id
    print(f"✅ Data Found: {ds_id}")
    ds_response = bedrock_agent.update_data_source(
        knowledgeBaseId=kb_id,
        dataSourceId=ds_id,
        name=ds_name,
        description="S3 data source",
        dataSourceConfiguration={
            'type': 'S3',
            's3Configuration': {
                'bucketArn': f'arn:aws:s3:::{bucket_name}' # Only process our specific file
            }
        }
    )
    
    # 8. Start ingestion job
    print("🔄 Starting ingestion job...")
    job_response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=kb_id,
        dataSourceId=ds_id
    )
    job_id = job_response['ingestionJob']['ingestionJobId']
    
    # Wait for ingestion to complete
    print("⏳ Waiting for ingestion to complete...")
    while True:
        job_status = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id,
            ingestionJobId=job_id
        )
        status = job_status['ingestionJob']['status']
        
        if status == 'COMPLETE':
            print("✅ Ingestion completed successfully")
            break
        elif status == 'FAILED':
            failure_reasons = job_status['ingestionJob'].get('failureReasons', ['Unknown error'])
            raise Exception(f"Ingestion failed: {failure_reasons}")
        elif status in ['IN_PROGRESS', 'STARTING']:
            print(f"⏳ Ingestion status: {status}")
            time.sleep(15)
        else:
            print(f"❓ Unexpected status: {status}")
            time.sleep(10)
    return kb_id

# def main():
#     """Main function to create the knowledge base"""
#     pdf_file = "../4-frameworks/strands-agents/utils/bedrock-agentcore-dg.pdf"
#     if not os.path.exists(pdf_file):
#         print(f"❌ Error: {pdf_file} not found")
#         return

#     # Get current AWS region
#     session = boto3.Session()
#     region = session.region_name
    
#     if not region:
#         print("❌ No AWS region configured. Please run: aws configure set region <your-region>")
#         return
    
#     print(f"🌍 Using AWS region: {region}")
#     print(f"🎯 Using S3 Vectors for cost-effective vector storage")
    
#     try:
#         kb_id = create_knowledge_base_with_s3_vectors(pdf_file, region=region)
#         print(f"\n✅ Knowledge Base ready for queries: {kb_id}")
        
#         # Write KB ID to file for notebook access
#         with open('../4-frameworks/strands-agents/kb_id.txt', 'w') as f:
#             f.write(kb_id)
        
#         print(f"💾 KB ID saved to kb_id.txt")
        
#         # Test the knowledge base
#         print(f"\n🧪 Testing Knowledge Base...")
#         bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=region)
        
#         test_query = "What is Amazon Bedrock AgentCore?"
#         response = bedrock_agent_runtime.retrieve(
#             knowledgeBaseId=kb_id,
#             retrievalQuery={'text': test_query},
#             retrievalConfiguration={'vectorSearchConfiguration': {'numberOfResults': 3}}
#         )
        
#         print(f"✅ Test query successful! Retrieved {len(response['retrievalResults'])} results")
        
#     except Exception as e:
#         print(f"\n❌ Error creating Knowledge Base: {e}")
#         raise

# if __name__ == "__main__":
#     main()