"""
Test API Keys Script

Tests each API key connection one by one.
Run this after adding each key to verify it works.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_pinecone():
    """Test Pinecone connection."""
    print("\n🔍 Testing Pinecone...")
    api_key = os.getenv("PINECONE_API_KEY", "")
    environment = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
    index_name = os.getenv("PINECONE_INDEX_NAME", "scholarsync-vectors")
    
    if not api_key or api_key == "your-pinecone-api-key":
        print("❌ PINECONE_API_KEY not set or still placeholder")
        return False
    
    try:
        from pinecone import Pinecone, ServerlessSpec
        pc = Pinecone(api_key=api_key)
        
        # List indexes
        indexes = pc.list_indexes()
        index_names = [idx.name for idx in indexes.indexes] if hasattr(indexes, 'indexes') else []
        
        print(f"✅ Pinecone connected!")
        print(f"   Environment: {environment}")
        print(f"   Available indexes: {index_names}")
        
        if index_name in index_names:
            print(f"✅ Index '{index_name}' found!")
            index = pc.Index(index_name)
            stats = index.describe_index_stats()
            print(f"   Index stats: {stats}")
            return True
        else:
            print(f"⚠️  Index '{index_name}' not found. Available: {index_names}")
            print(f"   You may need to create it in Pinecone dashboard")
            return False
            
    except ImportError:
        print("❌ pinecone package not installed. Run: pip install pinecone-client")
        return False
    except Exception as e:
        print(f"❌ Pinecone connection failed: {str(e)}")
        return False


def test_openai():
    """Test OpenAI connection."""
    print("\n🤖 Testing OpenAI...")
    api_key = os.getenv("OPENAI_API_KEY", "")
    
    if not api_key or api_key == "your-openai-api-key":
        print("❌ OPENAI_API_KEY not set or still placeholder")
        return False
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        # Test with a simple embedding
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input="test"
        )
        
        print("✅ OpenAI connected!")
        print(f"   Embedding dimensions: {len(response.data[0].embedding)}")
        return True
        
    except ImportError:
        print("❌ openai package not installed. Run: pip install openai")
        return False
    except Exception as e:
        print(f"❌ OpenAI connection failed: {str(e)}")
        return False


def test_gemini():
    """Test Gemini connection."""
    print("\n🌟 Testing Gemini...")
    api_key = os.getenv("GEMINI_API_KEY", "")
    
    if not api_key or api_key == "your-gemini-api-key":
        print("❌ GEMINI_API_KEY not set or still placeholder")
        return False
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # List available models
        models = genai.list_models()
        model_names = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
        print("✅ Gemini connected!")
        print(f"   Available models: {model_names[:3]}...")
        
        # Test with a simple generation
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("Say hello")
        
        print(f"   Test response: {response.text[:50]}...")
        return True
        
    except ImportError:
        print("❌ google-generativeai package not installed. Run: pip install google-generativeai")
        return False
    except Exception as e:
        print(f"❌ Gemini connection failed: {str(e)}")
        return False


def test_aws_s3():
    """Test AWS S3 connection."""
    print("\n☁️  Testing AWS S3...")
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    bucket_name = os.getenv("S3_BUCKET_NAME", "")
    region = os.getenv("AWS_REGION", "us-east-1")
    
    if not access_key or access_key == "your-aws-access-key":
        print("❌ AWS_ACCESS_KEY_ID not set or still placeholder")
        return False
    
    if not secret_key or secret_key == "your-aws-secret-key":
        print("❌ AWS_SECRET_ACCESS_KEY not set or still placeholder")
        return False
    
    try:
        import boto3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        # List buckets
        buckets = s3_client.list_buckets()
        bucket_names = [b['Name'] for b in buckets.get('Buckets', [])]
        
        print("✅ AWS S3 connected!")
        print(f"   Region: {region}")
        print(f"   Available buckets: {bucket_names}")
        
        if bucket_name and bucket_name in bucket_names:
            print(f"✅ Bucket '{bucket_name}' found!")
            return True
        elif bucket_name:
            print(f"⚠️  Bucket '{bucket_name}' not found. Available: {bucket_names}")
            return False
        else:
            print("⚠️  S3_BUCKET_NAME not set")
            return False
            
    except ImportError:
        print("❌ boto3 package not installed. Run: pip install boto3")
        return False
    except Exception as e:
        print(f"❌ AWS S3 connection failed: {str(e)}")
        return False


def test_supabase_storage():
    """Test Supabase Storage connection."""
    print("\n🗄️  Testing Supabase Storage...")
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_KEY", "")
    
    if not supabase_url:
        print("❌ SUPABASE_URL not set")
        return False
    
    if not supabase_key:
        print("❌ SUPABASE_KEY not set")
        return False
    
    try:
        from supabase import create_client, Client
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # List buckets
        buckets = supabase.storage.list_buckets()
        
        print("✅ Supabase Storage connected!")
        print(f"   URL: {supabase_url}")
        if buckets:
            bucket_names = [b.name for b in buckets]
            print(f"   Available buckets: {bucket_names}")
        return True
        
    except ImportError:
        print("❌ supabase package not installed. Run: pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Supabase Storage connection failed: {str(e)}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("API Keys Test Script")
    print("=" * 60)
    
    results = {
        "Pinecone": test_pinecone(),
        "OpenAI": test_openai(),
        "Gemini": test_gemini(),
        "AWS S3": test_aws_s3(),
        "Supabase Storage": test_supabase_storage(),
    }
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    for service, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{service:20} {status}")
    
    print("\n" + "=" * 60)
    
    # Count successes
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All API keys configured and working!")
    elif passed > 0:
        print(f"⚠️  {total - passed} API key(s) still need to be configured")
    else:
        print("❌ No API keys configured yet")


if __name__ == "__main__":
    main()


