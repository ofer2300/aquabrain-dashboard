"""
Hydraulic Engine Lambda Handler for Bedrock Agent Action Group
Hazen-Williams pressure loss calculations for fire sprinkler systems

Author: AquaBrain V10.0 Platinum
"""
import json
import math

# Fitting equivalent lengths (feet) based on pipe diameter
FITTING_EQUIV_LENGTHS = {
    'elbow_90': {1: 2.5, 1.25: 3, 1.5: 4, 2: 5, 2.5: 6, 3: 7, 4: 10, 6: 14, 8: 18},
    'elbow_45': {1: 1.2, 1.25: 1.5, 1.5: 2, 2: 2.5, 2.5: 3, 3: 3.5, 4: 5, 6: 7, 8: 9},
    'tee_flow': {1: 0.5, 1.25: 0.75, 1.5: 1, 2: 1.5, 2.5: 2, 3: 2.5, 4: 3, 6: 5, 8: 6},
    'tee_side': {1: 5, 1.25: 6, 1.5: 8, 2: 10, 2.5: 12, 3: 15, 4: 20, 6: 30, 8: 40},
    'gate_valve': {1: 0.5, 1.25: 0.6, 1.5: 0.8, 2: 1, 2.5: 1.2, 3: 1.5, 4: 2, 6: 3, 8: 4},
    'check_valve': {1: 5, 1.25: 6, 1.5: 7, 2: 10, 2.5: 12, 3: 15, 4: 18, 6: 25, 8: 35},
    'butterfly_valve': {1: 3, 1.25: 4, 1.5: 5, 2: 6, 2.5: 8, 3: 10, 4: 12, 6: 18, 8: 25}
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


def hazen_williams_loss(flow_gpm: float, diameter_inch: float, length_ft: float, c_factor: int = 120) -> float:
    """
    Calculate friction loss using Hazen-Williams formula

    P = 4.52 * Q^1.85 / (C^1.85 * d^4.87) * L

    Where:
    P = pressure loss (psi)
    Q = flow (gpm)
    C = Hazen-Williams coefficient
    d = internal diameter (inches)
    L = length (feet)
    """
    if diameter_inch <= 0 or flow_gpm <= 0:
        return 0.0

    pressure_loss = (4.52 * (flow_gpm ** 1.85)) / ((c_factor ** 1.85) * (diameter_inch ** 4.87)) * length_ft
    return round(pressure_loss, 3)


def calculate_velocity(flow_gpm: float, diameter_inch: float) -> float:
    """
    Calculate flow velocity in feet per second
    V = 0.4085 * Q / d^2
    """
    if diameter_inch <= 0:
        return 0.0
    velocity = 0.4085 * flow_gpm / (diameter_inch ** 2)
    return round(velocity, 2)


def get_fitting_equiv_length(fitting_type: str, diameter_inch: float) -> float:
    """Get equivalent length for fitting based on diameter"""
    if fitting_type not in FITTING_EQUIV_LENGTHS:
        return 0

    fitting_table = FITTING_EQUIV_LENGTHS[fitting_type]
    # Find closest diameter
    closest_dia = min(fitting_table.keys(), key=lambda x: abs(x - diameter_inch))
    return fitting_table[closest_dia]


def lambda_handler(event, context):
    """Bedrock Agent Lambda Handler"""
    action_group = event.get('actionGroup', 'HydraulicEngine')
    api_path = event.get('apiPath', '')
    http_method = event.get('httpMethod', 'POST')
    parameters = {p['name']: p['value'] for p in event.get('parameters', [])}
    request_body = event.get('requestBody', {}).get('content', {}).get('application/json', {}).get('properties', {})

    print(f"[HydraulicEngine] API Path: {api_path}")

    try:
        if api_path == '/calculate-pressure-loss':
            return handle_pressure_loss(action_group, api_path, http_method, request_body)
        elif api_path == '/analyze-path':
            return handle_analyze_path(action_group, api_path, http_method, request_body)
        else:
            return build_response(action_group, api_path, http_method, 400, {
                'error': f'Unknown API path: {api_path}'
            })
    except Exception as e:
        print(f"[HydraulicEngine] Error: {str(e)}")
        return build_response(action_group, api_path, http_method, 500, {
            'status': 'FAILED',
            'error': str(e)
        })


def handle_pressure_loss(action_group, api_path, http_method, body):
    """Handle /calculate-pressure-loss endpoint"""
    flow_gpm = float(body.get('flow_gpm', {}).get('value', 0))
    diameter_inch = float(body.get('pipe_diameter_inch', {}).get('value', 0))
    length_ft = float(body.get('pipe_length_ft', {}).get('value', 0))
    c_factor = int(body.get('c_factor', {}).get('value', 120))
    include_fittings = body.get('include_fittings', {}).get('value', 'true').lower() == 'true'
    fittings = json.loads(body.get('fittings', {}).get('value', '[]'))

    # Calculate equivalent length for fittings
    fittings_equiv_length = 0
    if include_fittings and fittings:
        for fitting in fittings:
            fitting_type = fitting.get('type', '')
            quantity = int(fitting.get('quantity', 1))
            equiv = get_fitting_equiv_length(fitting_type, diameter_inch)
            fittings_equiv_length += equiv * quantity

    total_equiv_length = length_ft + fittings_equiv_length

    # Calculate pressure loss
    pressure_loss = hazen_williams_loss(flow_gpm, diameter_inch, total_equiv_length, c_factor)

    # Calculate velocity
    velocity = calculate_velocity(flow_gpm, diameter_inch)
    velocity_warning = velocity > 20  # NFPA 13 recommends max 20 fps

    return build_response(action_group, api_path, http_method, 200, {
        'status': 'SUCCESS',
        'pressure_loss_psi': pressure_loss,
        'velocity_fps': velocity,
        'velocity_warning': velocity_warning,
        'equivalent_length_ft': round(total_equiv_length, 1),
        'formula_used': 'Hazen-Williams: P = 4.52 * Q^1.85 / (C^1.85 * d^4.87) * L'
    })


def handle_analyze_path(action_group, api_path, http_method, body):
    """Handle /analyze-path endpoint"""
    remote_area_demand = float(body.get('remote_area_demand_gpm', {}).get('value', 0))
    remote_area_pressure = float(body.get('remote_area_pressure_psi', {}).get('value', 7))
    hose_stream = float(body.get('hose_stream_allowance_gpm', {}).get('value', 250))
    pipe_segments = json.loads(body.get('pipe_segments', {}).get('value', '[]'))

    total_friction_loss = 0
    total_elevation_loss = 0
    current_flow = remote_area_demand
    segment_results = []
    max_velocity = 0

    for segment in pipe_segments:
        diameter = float(segment.get('diameter_inch', 2))
        length = float(segment.get('length_ft', 10))
        elevation = float(segment.get('elevation_change_ft', 0))
        additional_flow = float(segment.get('additional_flow_gpm', 0))
        c_factor = int(segment.get('c_factor', 120))
        segment_id = segment.get('segment_id', f'seg_{len(segment_results)+1}')

        current_flow += additional_flow

        # Calculate friction loss
        friction_loss = hazen_williams_loss(current_flow, diameter, length, c_factor)
        total_friction_loss += friction_loss

        # Calculate elevation loss (0.433 psi per foot of elevation)
        elev_loss = elevation * 0.433
        total_elevation_loss += elev_loss

        # Calculate velocity
        velocity = calculate_velocity(current_flow, diameter)
        max_velocity = max(max_velocity, velocity)

        segment_results.append({
            'segment_id': segment_id,
            'friction_loss_psi': round(friction_loss, 2),
            'cumulative_flow_gpm': round(current_flow, 1),
            'velocity_fps': velocity
        })

    # Total demand
    total_demand = current_flow + hose_stream

    # Total pressure required
    total_pressure = remote_area_pressure + total_friction_loss + total_elevation_loss

    # Traffic light determination
    if max_velocity > 25 or total_pressure > 150:
        traffic_light = 'RED'
    elif max_velocity > 20 or total_pressure > 120:
        traffic_light = 'YELLOW'
    else:
        traffic_light = 'GREEN'

    return build_response(action_group, api_path, http_method, 200, {
        'status': 'SUCCESS',
        'total_demand_gpm': round(total_demand, 1),
        'total_pressure_required_psi': round(total_pressure, 2),
        'friction_loss_psi': round(total_friction_loss, 2),
        'elevation_loss_psi': round(total_elevation_loss, 2),
        'segment_results': segment_results,
        'traffic_light': traffic_light
    })
