"""
Hebrew Fixer Lambda Handler for Bedrock Agent Action Group
Fixes Windows-1255 Hebrew encoding in DXF/DWG files

Author: AquaBrain V10.0 Platinum
"""
import json
import os
import boto3
import ezdxf
from urllib.parse import urlparse
import tempfile
import time

s3 = boto3.client('s3')

# Bedrock Agent response format
def build_response(action_group, api_path, http_method, response_code, response_body):
    """Build Bedrock Agent compliant response"""
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': action_group,
            'apiPath': api_path,
            'httpMethod': http_method,
            'httpStatusCode': response_code,
            'responseBody': {
                'application/json': {
                    'body': json.dumps(response_body)
                }
            }
        }
    }


def parse_s3_uri(s3_uri: str) -> tuple:
    """Parse S3 URI into bucket and key"""
    parsed = urlparse(s3_uri)
    return parsed.netloc, parsed.path.lstrip('/')


def fix_hebrew_encoding(text: str) -> str:
    """Convert Windows-1255 garbled Hebrew to UTF-8"""
    try:
        # Try to detect and fix Windows-1255 encoding
        fixed = text.encode('latin-1').decode('windows-1255')
        return fixed
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def lambda_handler(event, context):
    """
    Bedrock Agent Lambda Handler

    Event structure from Bedrock Agent:
    {
        "messageVersion": "1.0",
        "agent": {...},
        "inputText": "...",
        "sessionId": "...",
        "actionGroup": "FileSanitization",
        "apiPath": "/fix-hebrew",
        "httpMethod": "POST",
        "parameters": [...],
        "requestBody": {...}
    }
    """
    start_time = time.time()

    action_group = event.get('actionGroup', 'FileSanitization')
    api_path = event.get('apiPath', '')
    http_method = event.get('httpMethod', 'POST')
    parameters = {p['name']: p['value'] for p in event.get('parameters', [])}

    print(f"[HebrewFixer] API Path: {api_path}, Parameters: {parameters}")

    try:
        if api_path == '/fix-hebrew':
            return handle_fix_hebrew(action_group, api_path, http_method, parameters, start_time)
        elif api_path == '/extract-geometry':
            return handle_extract_geometry(action_group, api_path, http_method, parameters)
        else:
            return build_response(action_group, api_path, http_method, 400, {
                'error': f'Unknown API path: {api_path}'
            })

    except Exception as e:
        print(f"[HebrewFixer] Error: {str(e)}")
        return build_response(action_group, api_path, http_method, 500, {
            'status': 'FAILED',
            'error': str(e)
        })


def handle_fix_hebrew(action_group, api_path, http_method, parameters, start_time):
    """Handle /fix-hebrew endpoint"""
    s3_uri = parameters.get('s3_uri')
    output_suffix = parameters.get('output_suffix', '_fixed')

    if not s3_uri:
        return build_response(action_group, api_path, http_method, 400, {
            'error': 'Missing required parameter: s3_uri'
        })

    # Parse S3 URI
    bucket, key = parse_s3_uri(s3_uri)

    # Download file to temp location
    with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp_input:
        s3.download_file(bucket, key, tmp_input.name)
        input_path = tmp_input.name

    # Process DXF file
    try:
        doc = ezdxf.readfile(input_path)
        entities_fixed = 0

        # Fix Hebrew in MTEXT entities
        for mtext in doc.modelspace().query('MTEXT'):
            original = mtext.dxf.text
            fixed = fix_hebrew_encoding(original)
            if fixed != original:
                mtext.dxf.text = fixed
                entities_fixed += 1

        # Fix Hebrew in TEXT entities
        for text in doc.modelspace().query('TEXT'):
            original = text.dxf.text
            fixed = fix_hebrew_encoding(original)
            if fixed != original:
                text.dxf.text = fixed
                entities_fixed += 1

        # Fix in dimension texts
        for dim in doc.modelspace().query('DIMENSION'):
            if hasattr(dim.dxf, 'text') and dim.dxf.text:
                original = dim.dxf.text
                fixed = fix_hebrew_encoding(original)
                if fixed != original:
                    dim.dxf.text = fixed
                    entities_fixed += 1

        # Save fixed file
        with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp_output:
            doc.saveas(tmp_output.name)
            output_path = tmp_output.name

        # Generate output key
        base_key = key.rsplit('.', 1)[0]
        ext = key.rsplit('.', 1)[1] if '.' in key else 'dxf'
        output_key = f"{base_key}{output_suffix}.{ext}"

        # Upload to output bucket
        output_bucket = os.environ.get('OUTPUT_BUCKET', bucket)
        s3.upload_file(output_path, output_bucket, output_key)

        processing_time = int((time.time() - start_time) * 1000)

        return build_response(action_group, api_path, http_method, 200, {
            'status': 'SUCCESS',
            'fixed_s3_uri': f's3://{output_bucket}/{output_key}',
            'entities_fixed': entities_fixed,
            'processing_time_ms': processing_time
        })

    finally:
        # Cleanup temp files
        import os as os_module
        if os_module.path.exists(input_path):
            os_module.remove(input_path)


def handle_extract_geometry(action_group, api_path, http_method, parameters):
    """Handle /extract-geometry endpoint"""
    s3_uri = parameters.get('s3_uri')
    include_text = parameters.get('include_text', 'true').lower() == 'true'
    include_dimensions = parameters.get('include_dimensions', 'true').lower() == 'true'

    if not s3_uri:
        return build_response(action_group, api_path, http_method, 400, {
            'error': 'Missing required parameter: s3_uri'
        })

    bucket, key = parse_s3_uri(s3_uri)

    with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp:
        s3.download_file(bucket, key, tmp.name)
        doc = ezdxf.readfile(tmp.name)

    msp = doc.modelspace()

    # Count entities
    polylines = list(msp.query('LWPOLYLINE')) + list(msp.query('POLYLINE'))
    texts = list(msp.query('TEXT')) + list(msp.query('MTEXT')) if include_text else []

    # Get layers
    layers = [layer.dxf.name for layer in doc.layers]

    # Calculate bounding box
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')

    for entity in msp:
        try:
            if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'insert'):
                x, y = entity.dxf.insert.x, entity.dxf.insert.y
                min_x, min_y = min(min_x, x), min(min_y, y)
                max_x, max_y = max(max_x, x), max(max_y, y)
        except:
            pass

    # Save geometry JSON
    geometry_data = {
        'source_file': s3_uri,
        'polylines_count': len(polylines),
        'text_entities_count': len(texts),
        'layers': layers,
        'bounding_box': {
            'min_x': min_x if min_x != float('inf') else 0,
            'min_y': min_y if min_y != float('inf') else 0,
            'max_x': max_x if max_x != float('-inf') else 0,
            'max_y': max_y if max_y != float('-inf') else 0
        }
    }

    # Upload geometry JSON
    output_bucket = os.environ.get('OUTPUT_BUCKET', bucket)
    output_key = key.rsplit('.', 1)[0] + '_geometry.json'

    s3.put_object(
        Bucket=output_bucket,
        Key=output_key,
        Body=json.dumps(geometry_data, indent=2),
        ContentType='application/json'
    )

    return build_response(action_group, api_path, http_method, 200, {
        'status': 'SUCCESS',
        'polylines_count': len(polylines),
        'text_entities_count': len(texts),
        'layers': layers,
        'bounding_box': geometry_data['bounding_box'],
        'output_s3_uri': f's3://{output_bucket}/{output_key}'
    })
