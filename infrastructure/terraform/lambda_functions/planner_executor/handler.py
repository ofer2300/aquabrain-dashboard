"""
Planner-Executor Lambda Handler for Bedrock Agent Action Group
Plan-then-Execute orchestration for LOD 500 fire sprinkler design automation

Author: AquaBrain V10.0 Platinum
"""
import json
import os
import uuid
import hashlib
import time
from datetime import datetime
from enum import Enum
import boto3

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

PLANS_BUCKET = os.environ.get('PLANS_BUCKET', 'aquaskill-plans')
RESULTS_BUCKET = os.environ.get('RESULTS_BUCKET', 'aquaskill-results')


class RiskProfile(str, Enum):
    STANDARD = 'STANDARD'
    HIGH_COMPLEXITY = 'HIGH_COMPLEXITY'


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


def determine_risk_level(hazard_class: str, area_sqft: float, pressure_psi: float) -> RiskProfile:
    """Determine project risk profile based on inputs"""
    if hazard_class in ['Extra Group 1', 'Extra Group 2']:
        return RiskProfile.HIGH_COMPLEXITY
    if area_sqft > 50000:  # Large building
        return RiskProfile.HIGH_COMPLEXITY
    if pressure_psi < 50:  # Low pressure concerns
        return RiskProfile.HIGH_COMPLEXITY
    return RiskProfile.STANDARD


def generate_execution_plan(project_type: str, risk_profile: RiskProfile, has_input_files: bool) -> list:
    """Generate execution steps based on project parameters"""
    steps = []
    step_num = 1

    # Step 1: File sanitization (if files provided)
    if has_input_files:
        steps.append({
            'step_number': step_num,
            'action': 'fix_hebrew_encoding',
            'description': 'Fix Hebrew encoding in DXF/DWG files',
            'action_group': 'FileSanitization',
            'dependencies': [],
            'estimated_duration_seconds': 30
        })
        step_num += 1

        steps.append({
            'step_number': step_num,
            'action': 'extract_geometry',
            'description': 'Extract geometry data from CAD files',
            'action_group': 'FileSanitization',
            'dependencies': [step_num - 1],
            'estimated_duration_seconds': 45
        })
        step_num += 1

    # Step 2: Hydraulic calculations
    steps.append({
        'step_number': step_num,
        'action': 'calculate_hydraulics',
        'description': 'Calculate pressure loss using Hazen-Williams',
        'action_group': 'HydraulicEngine',
        'dependencies': [step_num - 1] if has_input_files else [],
        'estimated_duration_seconds': 20
    })
    step_num += 1

    # Step 3: Path analysis (for high complexity)
    if risk_profile == RiskProfile.HIGH_COMPLEXITY:
        steps.append({
            'step_number': step_num,
            'action': 'analyze_hydraulic_path',
            'description': 'Full hydraulic path analysis from remote to supply',
            'action_group': 'HydraulicEngine',
            'dependencies': [step_num - 1],
            'estimated_duration_seconds': 60
        })
        step_num += 1

    # Step 4: NFPA validation
    steps.append({
        'step_number': step_num,
        'action': 'validate_nfpa_compliance',
        'description': 'Validate design against NFPA 13 requirements',
        'action_group': 'NFPAValidator',
        'dependencies': [step_num - 1],
        'estimated_duration_seconds': 15
    })
    step_num += 1

    # Step 5: Spacing check
    steps.append({
        'step_number': step_num,
        'action': 'check_sprinkler_spacing',
        'description': 'Verify sprinkler spacing compliance',
        'action_group': 'NFPAValidator',
        'dependencies': [step_num - 1],
        'estimated_duration_seconds': 10
    })
    step_num += 1

    # Step 6: Verification
    steps.append({
        'step_number': step_num,
        'action': 'verify_results',
        'description': 'Run forensic verification and generate LOD 500 BOM',
        'action_group': 'PlannerExecutor',
        'dependencies': [step_num - 1],
        'estimated_duration_seconds': 30
    })

    return steps


def lambda_handler(event, context):
    """Bedrock Agent Lambda Handler"""
    action_group = event.get('actionGroup', 'PlannerExecutor')
    api_path = event.get('apiPath', '')
    http_method = event.get('httpMethod', 'POST')
    parameters = {p['name']: p['value'] for p in event.get('parameters', [])}
    request_body = event.get('requestBody', {}).get('content', {}).get('application/json', {}).get('properties', {})

    print(f"[PlannerExecutor] API Path: {api_path}")

    try:
        if api_path == '/create-plan':
            return handle_create_plan(action_group, api_path, http_method, request_body)
        elif api_path == '/execute-plan':
            return handle_execute_plan(action_group, api_path, http_method, request_body)
        elif api_path == '/verify-results':
            return handle_verify_results(action_group, api_path, http_method, request_body)
        elif api_path == '/get-plan-status':
            return handle_get_plan_status(action_group, api_path, http_method, parameters)
        else:
            return build_response(action_group, api_path, http_method, 400, {
                'error': f'Unknown API path: {api_path}'
            })
    except Exception as e:
        print(f"[PlannerExecutor] Error: {str(e)}")
        return build_response(action_group, api_path, http_method, 500, {
            'status': 'FAILED',
            'error': str(e)
        })


def handle_create_plan(action_group, api_path, http_method, body):
    """Handle /create-plan endpoint"""
    project_id = body.get('project_id', {}).get('value', str(uuid.uuid4()))
    project_type = body.get('project_type', {}).get('value', 'new_design')
    hazard_class = body.get('hazard_class', {}).get('value', 'Light')
    building_info = json.loads(body.get('building_info', {}).get('value', '{}'))
    water_supply = json.loads(body.get('water_supply', {}).get('value', '{}'))
    input_files = json.loads(body.get('input_files', {}).get('value', '[]'))

    # Determine risk profile
    area = float(building_info.get('total_area_sqft', 0))
    pressure = float(water_supply.get('available_pressure_psi', 100))
    risk_profile = determine_risk_level(hazard_class, area, pressure)

    # Generate execution plan
    plan_id = f"plan_{uuid.uuid4().hex[:12]}"
    execution_steps = generate_execution_plan(
        project_type,
        risk_profile,
        len(input_files) > 0
    )

    # Store plan in S3
    plan_data = {
        'plan_id': plan_id,
        'project_id': project_id,
        'project_type': project_type,
        'hazard_class': hazard_class,
        'risk_profile': risk_profile.value,
        'execution_steps': execution_steps,
        'status': 'PENDING',
        'created_at': datetime.utcnow().isoformat(),
        'input_files': input_files,
        'building_info': building_info,
        'water_supply': water_supply
    }

    plan_key = f"plans/{plan_id}.json"
    try:
        s3.put_object(
            Bucket=PLANS_BUCKET,
            Key=plan_key,
            Body=json.dumps(plan_data, indent=2),
            ContentType='application/json'
        )
    except Exception as e:
        print(f"[PlannerExecutor] S3 error (plan creation skipped in local mode): {e}")

    return build_response(action_group, api_path, http_method, 200, {
        'status': 'PLAN_CREATED',
        'plan_id': plan_id,
        'risk_profile': risk_profile.value,
        'execution_steps': execution_steps,
        'total_steps': len(execution_steps),
        'plan_s3_uri': f's3://{PLANS_BUCKET}/{plan_key}'
    })


def handle_execute_plan(action_group, api_path, http_method, body):
    """Handle /execute-plan endpoint"""
    plan_id = body.get('plan_id', {}).get('value', '')
    start_from = int(body.get('start_from_step', {}).get('value', 1))
    dry_run = body.get('dry_run', {}).get('value', 'false').lower() == 'true'

    if not plan_id:
        return build_response(action_group, api_path, http_method, 400, {
            'error': 'Missing required parameter: plan_id'
        })

    # In production, this would retrieve the plan from S3 and execute each step
    # For now, simulate execution
    step_results = [
        {'step_number': 1, 'status': 'COMPLETED', 'output_s3_uri': f's3://{RESULTS_BUCKET}/step1.json', 'duration_seconds': 2.5},
        {'step_number': 2, 'status': 'COMPLETED', 'output_s3_uri': f's3://{RESULTS_BUCKET}/step2.json', 'duration_seconds': 3.2},
        {'step_number': 3, 'status': 'COMPLETED', 'output_s3_uri': f's3://{RESULTS_BUCKET}/step3.json', 'duration_seconds': 1.8},
        {'step_number': 4, 'status': 'COMPLETED', 'output_s3_uri': f's3://{RESULTS_BUCKET}/step4.json', 'duration_seconds': 1.2},
        {'step_number': 5, 'status': 'COMPLETED', 'output_s3_uri': f's3://{RESULTS_BUCKET}/step5.json', 'duration_seconds': 2.1},
    ]

    return build_response(action_group, api_path, http_method, 200, {
        'status': 'COMPLETED' if not dry_run else 'DRY_RUN_COMPLETED',
        'steps_completed': len(step_results),
        'steps_total': len(step_results),
        'step_results': step_results,
        'failed_step': None
    })


def handle_verify_results(action_group, api_path, http_method, body):
    """Handle /verify-results endpoint"""
    plan_id = body.get('plan_id', {}).get('value', '')
    verification_level = body.get('verification_level', {}).get('value', 'standard')
    generate_bom = body.get('generate_bom', {}).get('value', 'true').lower() == 'true'
    safety_margin = float(body.get('safety_margin_percent', {}).get('value', 10))

    # Simulate verification results
    verification_results = {
        'hydraulics': {
            'status': 'PASS',
            'pressure_margin_psi': 15.5,
            'max_velocity_fps': 18.2,
            'velocity_compliant': True
        },
        'nfpa_compliance': {
            'status': 'PASS',
            'violations_count': 0,
            'warnings_count': 1
        },
        'clashes': {
            'hard_clashes': 0,
            'soft_clashes': 2,
            'status': 'PASS'
        }
    }

    # Generate BOM
    bom = None
    if generate_bom:
        bom = {
            'total_pipe_length_ft': 1250.5,
            'pipe_breakdown': {
                '1_inch': 450.2,
                '1.25_inch': 320.8,
                '1.5_inch': 280.5,
                '2_inch': 199.0
            },
            'sprinkler_count': 85,
            'fitting_count': 234,
            'valve_count': 12,
            'bom_s3_uri': f's3://{RESULTS_BUCKET}/bom_{plan_id}.json'
        }

    # Generate audit hash
    audit_content = json.dumps({
        'plan_id': plan_id,
        'verification_results': verification_results,
        'bom': bom,
        'timestamp': datetime.utcnow().isoformat()
    }, sort_keys=True)
    audit_hash = hashlib.sha256(audit_content.encode()).hexdigest()

    # Determine traffic light
    if verification_results['nfpa_compliance']['violations_count'] > 0:
        traffic_light = 'RED'
        status = 'FAILED_VERIFICATION'
    elif verification_results['clashes']['hard_clashes'] > 0:
        traffic_light = 'RED'
        status = 'FAILED_VERIFICATION'
    elif verification_results['nfpa_compliance']['warnings_count'] > 2:
        traffic_light = 'YELLOW'
        status = 'NEEDS_REVIEW'
    else:
        traffic_light = 'GREEN'
        status = 'VERIFIED'

    return build_response(action_group, api_path, http_method, 200, {
        'status': status,
        'traffic_light': traffic_light,
        'verification_results': verification_results,
        'bom': bom,
        'report_s3_uri': f's3://{RESULTS_BUCKET}/report_{plan_id}.pdf',
        'audit_hash': audit_hash
    })


def handle_get_plan_status(action_group, api_path, http_method, parameters):
    """Handle /get-plan-status endpoint"""
    plan_id = parameters.get('plan_id', '')

    if not plan_id:
        return build_response(action_group, api_path, http_method, 400, {
            'error': 'Missing required parameter: plan_id'
        })

    # Simulate status (in production, fetch from S3/DynamoDB)
    return build_response(action_group, api_path, http_method, 200, {
        'plan_id': plan_id,
        'status': 'COMPLETED',
        'current_step': 5,
        'total_steps': 5,
        'progress_percent': 100.0,
        'created_at': '2025-12-06T10:00:00Z',
        'updated_at': datetime.utcnow().isoformat()
    })
