"""
NFPA Validator Lambda Handler for Bedrock Agent Action Group
Validates fire sprinkler designs against NFPA 13 (2025 Edition)

Author: AquaBrain V10.0 Platinum
"""
import json
import math

# NFPA 13 Tables - Design Criteria
NFPA_DESIGN_TABLES = {
    'Light': {
        'density_gpm_sqft': 0.10,
        'design_area_sqft': 1500,
        'max_coverage_sqft': 225,
        'max_spacing_ft': 15.0,
        'min_spacing_ft': 6.0,
        'max_distance_to_wall_ft': 7.5,
        'hose_stream_gpm': 100,
        'duration_min': 30,
        'nfpa_section': '10.2.1'
    },
    'Ordinary Group 1': {
        'density_gpm_sqft': 0.15,
        'design_area_sqft': 1500,
        'max_coverage_sqft': 130,
        'max_spacing_ft': 15.0,
        'min_spacing_ft': 6.0,
        'max_distance_to_wall_ft': 7.5,
        'hose_stream_gpm': 250,
        'duration_min': 60,
        'nfpa_section': '10.2.2'
    },
    'Ordinary Group 2': {
        'density_gpm_sqft': 0.20,
        'design_area_sqft': 1500,
        'max_coverage_sqft': 130,
        'max_spacing_ft': 15.0,
        'min_spacing_ft': 6.0,
        'max_distance_to_wall_ft': 7.5,
        'hose_stream_gpm': 250,
        'duration_min': 60,
        'nfpa_section': '10.2.2'
    },
    'Extra Group 1': {
        'density_gpm_sqft': 0.30,
        'design_area_sqft': 2500,
        'max_coverage_sqft': 100,
        'max_spacing_ft': 12.0,
        'min_spacing_ft': 6.0,
        'max_distance_to_wall_ft': 6.0,
        'hose_stream_gpm': 500,
        'duration_min': 90,
        'nfpa_section': '10.2.3'
    },
    'Extra Group 2': {
        'density_gpm_sqft': 0.40,
        'design_area_sqft': 2500,
        'max_coverage_sqft': 100,
        'max_spacing_ft': 12.0,
        'min_spacing_ft': 6.0,
        'max_distance_to_wall_ft': 6.0,
        'hose_stream_gpm': 500,
        'duration_min': 120,
        'nfpa_section': '10.2.3'
    }
}

# Israeli Standard reference
ISRAELI_STANDARD = {
    'code': 'ת"י 1596',
    'fire_water_tank_liters_per_sqm': 7.5,
    'minimum_tank_volume_m3': 50
}


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


def lambda_handler(event, context):
    """Bedrock Agent Lambda Handler"""
    action_group = event.get('actionGroup', 'NFPAValidator')
    api_path = event.get('apiPath', '')
    http_method = event.get('httpMethod', 'POST')
    parameters = {p['name']: p['value'] for p in event.get('parameters', [])}
    request_body = event.get('requestBody', {}).get('content', {}).get('application/json', {}).get('properties', {})

    print(f"[NFPAValidator] API Path: {api_path}")

    try:
        if api_path == '/validate-design':
            return handle_validate_design(action_group, api_path, http_method, request_body)
        elif api_path == '/check-spacing':
            return handle_check_spacing(action_group, api_path, http_method, request_body)
        elif api_path == '/query-requirement':
            return handle_query_requirement(action_group, api_path, http_method, parameters)
        else:
            return build_response(action_group, api_path, http_method, 400, {
                'error': f'Unknown API path: {api_path}'
            })
    except Exception as e:
        print(f"[NFPAValidator] Error: {str(e)}")
        return build_response(action_group, api_path, http_method, 500, {
            'status': 'FAILED',
            'error': str(e)
        })


def handle_validate_design(action_group, api_path, http_method, body):
    """Handle /validate-design endpoint"""
    hazard_class = body.get('hazard_class', {}).get('value', 'Light')
    sprinkler_layout = json.loads(body.get('sprinkler_layout', {}).get('value', '{}'))
    ceiling_height = float(body.get('ceiling_height_ft', {}).get('value', 10))
    obstructions = json.loads(body.get('obstructions', {}).get('value', '[]'))

    if hazard_class not in NFPA_DESIGN_TABLES:
        return build_response(action_group, api_path, http_method, 400, {
            'error': f'Unknown hazard class: {hazard_class}'
        })

    criteria = NFPA_DESIGN_TABLES[hazard_class]
    violations = []
    warnings = []

    # Check coverage per head
    coverage = float(sprinkler_layout.get('coverage_sqft_per_head', 0))
    if coverage > criteria['max_coverage_sqft']:
        violations.append({
            'rule_id': 'COVERAGE_EXCEEDED',
            'nfpa_section': criteria['nfpa_section'],
            'severity': 'CRITICAL',
            'description': f'Coverage per head ({coverage} sqft) exceeds maximum ({criteria["max_coverage_sqft"]} sqft)',
            'affected_elements': ['all_sprinklers'],
            'remediation': 'Add more sprinkler heads to reduce coverage area'
        })

    # Check spacing
    spacing = float(sprinkler_layout.get('spacing_ft', 0))
    if spacing > criteria['max_spacing_ft']:
        violations.append({
            'rule_id': 'SPACING_EXCEEDED',
            'nfpa_section': criteria['nfpa_section'],
            'severity': 'CRITICAL',
            'description': f'Spacing ({spacing} ft) exceeds maximum ({criteria["max_spacing_ft"]} ft)',
            'affected_elements': ['all_sprinklers'],
            'remediation': 'Reduce spacing between sprinkler heads'
        })
    elif spacing < criteria['min_spacing_ft']:
        violations.append({
            'rule_id': 'SPACING_INSUFFICIENT',
            'nfpa_section': criteria['nfpa_section'],
            'severity': 'MAJOR',
            'description': f'Spacing ({spacing} ft) below minimum ({criteria["min_spacing_ft"]} ft)',
            'affected_elements': ['all_sprinklers'],
            'remediation': 'Increase spacing between sprinkler heads'
        })

    # Check deflector distance to ceiling
    positions = sprinkler_layout.get('positions', [])
    for pos in positions:
        deflector_dist = float(pos.get('deflector_to_ceiling_inch', 0))
        if deflector_dist < 1:
            violations.append({
                'rule_id': 'DEFLECTOR_TOO_CLOSE',
                'nfpa_section': '8.6.2',
                'severity': 'MAJOR',
                'description': f'Deflector distance to ceiling ({deflector_dist}") below minimum (1")',
                'affected_elements': [pos.get('id', 'unknown')],
                'remediation': 'Lower sprinkler head to maintain minimum deflector distance'
            })
        elif deflector_dist > 12:
            violations.append({
                'rule_id': 'DEFLECTOR_TOO_FAR',
                'nfpa_section': '8.6.2',
                'severity': 'MAJOR',
                'description': f'Deflector distance to ceiling ({deflector_dist}") exceeds maximum (12")',
                'affected_elements': [pos.get('id', 'unknown')],
                'remediation': 'Raise sprinkler head closer to ceiling'
            })

    # Check obstructions
    for obstruction in obstructions:
        obs_width = float(obstruction.get('width_inch', 0))
        obs_distance = float(obstruction.get('distance_from_sprinkler_inch', 0))

        # Rule of three: horizontal distance must be >= 3x obstruction width
        min_distance = obs_width * 3
        if obs_distance < min_distance:
            warnings.append({
                'nfpa_section': '8.7',
                'message': f'Obstruction {obs_width}" wide requires minimum {min_distance}" horizontal distance from sprinkler'
            })

    # Calculate compliance score
    critical_count = sum(1 for v in violations if v['severity'] == 'CRITICAL')
    major_count = sum(1 for v in violations if v['severity'] == 'MAJOR')
    minor_count = sum(1 for v in violations if v['severity'] == 'MINOR')

    compliance_score = 100 - (critical_count * 30) - (major_count * 15) - (minor_count * 5)
    compliance_score = max(0, compliance_score)

    # Determine status
    if critical_count > 0:
        status = 'NON_COMPLIANT'
        traffic_light = 'RED'
    elif major_count > 0 or len(warnings) > 2:
        status = 'NEEDS_REVIEW'
        traffic_light = 'YELLOW'
    else:
        status = 'COMPLIANT'
        traffic_light = 'GREEN'

    return build_response(action_group, api_path, http_method, 200, {
        'status': status,
        'traffic_light': traffic_light,
        'violations': violations,
        'warnings': warnings,
        'compliance_score': compliance_score
    })


def handle_check_spacing(action_group, api_path, http_method, body):
    """Handle /check-spacing endpoint"""
    hazard_class = body.get('hazard_class', {}).get('value', 'Light')
    positions = json.loads(body.get('sprinkler_positions', {}).get('value', '[]'))
    walls = json.loads(body.get('wall_positions', {}).get('value', '[]'))

    if hazard_class not in NFPA_DESIGN_TABLES:
        hazard_class = 'Light'

    criteria = NFPA_DESIGN_TABLES[hazard_class]
    violations = []

    # Check spacing between heads
    for i, pos1 in enumerate(positions):
        for j, pos2 in enumerate(positions):
            if i >= j:
                continue

            x1, y1 = float(pos1.get('x', 0)), float(pos1.get('y', 0))
            x2, y2 = float(pos2.get('x', 0)), float(pos2.get('y', 0))

            distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

            if distance > criteria['max_spacing_ft']:
                violations.append({
                    'sprinkler_id': f"{pos1.get('id', i)}-{pos2.get('id', j)}",
                    'issue': 'SPACING_EXCEEDED',
                    'actual_value_ft': round(distance, 2),
                    'required_value_ft': criteria['max_spacing_ft']
                })
            elif distance < criteria['min_spacing_ft']:
                violations.append({
                    'sprinkler_id': f"{pos1.get('id', i)}-{pos2.get('id', j)}",
                    'issue': 'SPACING_BELOW_MINIMUM',
                    'actual_value_ft': round(distance, 2),
                    'required_value_ft': criteria['min_spacing_ft']
                })

    # Check distance to walls
    for pos in positions:
        px, py = float(pos.get('x', 0)), float(pos.get('y', 0))

        for wall in walls:
            # Simple perpendicular distance to wall line
            x1, y1 = float(wall.get('x1', 0)), float(wall.get('y1', 0))
            x2, y2 = float(wall.get('x2', 0)), float(wall.get('y2', 0))

            # Calculate distance to line segment
            wall_len = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if wall_len > 0:
                dist = abs((y2 - y1) * px - (x2 - x1) * py + x2 * y1 - y2 * x1) / wall_len

                if dist > criteria['max_distance_to_wall_ft']:
                    violations.append({
                        'sprinkler_id': pos.get('id', 'unknown'),
                        'issue': 'DISTANCE_TO_WALL_EXCEEDED',
                        'actual_value_ft': round(dist, 2),
                        'required_value_ft': criteria['max_distance_to_wall_ft']
                    })

    return build_response(action_group, api_path, http_method, 200, {
        'status': 'PASS' if not violations else 'FAIL',
        'min_spacing_required_ft': criteria['min_spacing_ft'],
        'max_spacing_allowed_ft': criteria['max_spacing_ft'],
        'max_distance_to_wall_ft': criteria['max_distance_to_wall_ft'],
        'violations': violations,
        'nfpa_reference': f"NFPA 13 Section {criteria['nfpa_section']}"
    })


def handle_query_requirement(action_group, api_path, http_method, parameters):
    """Handle /query-requirement endpoint"""
    section = parameters.get('section', '')
    topic = parameters.get('topic', '').lower()

    response = {
        'section': section,
        'title': '',
        'requirements': [],
        'tables': [],
        'israeli_standard_reference': ''
    }

    # Query by section number
    if section:
        if section.startswith('10.2.1'):
            response['title'] = 'Light Hazard Occupancies - Design Criteria'
            response['requirements'] = [
                'Design density: 0.10 gpm/sqft over 1,500 sqft',
                'Maximum coverage per head: 225 sqft',
                'Maximum spacing: 15 ft',
                'Minimum spacing: 6 ft',
                'Hose stream allowance: 100 gpm',
                'Duration: 30 minutes'
            ]
            response['tables'] = [{'table_id': '10.2.1', 'data': NFPA_DESIGN_TABLES['Light']}]
        elif section.startswith('10.2.2'):
            response['title'] = 'Ordinary Hazard Occupancies - Design Criteria'
            response['requirements'] = [
                'OH-1: 0.15 gpm/sqft, OH-2: 0.20 gpm/sqft over 1,500 sqft',
                'Maximum coverage per head: 130 sqft',
                'Maximum spacing: 15 ft',
                'Hose stream allowance: 250 gpm',
                'Duration: 60 minutes'
            ]
            response['tables'] = [
                {'table_id': '10.2.2a', 'data': NFPA_DESIGN_TABLES['Ordinary Group 1']},
                {'table_id': '10.2.2b', 'data': NFPA_DESIGN_TABLES['Ordinary Group 2']}
            ]
        elif section.startswith('8.6'):
            response['title'] = 'Deflector Distance to Ceiling'
            response['requirements'] = [
                'Standard spray sprinklers: 1" to 12" below ceiling',
                'Pendent sprinklers in smooth ceiling: 1" to 6" recommended',
                'Extended coverage: per manufacturer listing'
            ]

    # Query by topic
    if topic:
        if 'spacing' in topic or 'distance' in topic:
            response['title'] = 'Sprinkler Spacing Requirements'
            response['requirements'] = [
                'Light Hazard: Max 15 ft, Min 6 ft',
                'Ordinary Hazard: Max 15 ft, Min 6 ft',
                'Extra Hazard: Max 12 ft, Min 6 ft',
                'Max distance to wall: half the allowable spacing'
            ]
        elif 'obstruction' in topic:
            response['title'] = 'Obstruction Rules (NFPA 13 Section 8.7)'
            response['requirements'] = [
                'Rule of three: Min horizontal distance = 3x obstruction width',
                'Continuous obstructions > 4 ft wide require additional sprinklers below',
                'Beam pockets > 12" deep require additional coverage'
            ]
        elif 'tank' in topic or 'israeli' in topic or 'israel' in topic:
            response['israeli_standard_reference'] = ISRAELI_STANDARD['code']
            response['requirements'] = [
                f"Fire water tank sizing: {ISRAELI_STANDARD['fire_water_tank_liters_per_sqm']} L/sqm",
                f"Minimum tank volume: {ISRAELI_STANDARD['minimum_tank_volume_m3']} m³"
            ]

    return build_response(action_group, api_path, http_method, 200, response)
