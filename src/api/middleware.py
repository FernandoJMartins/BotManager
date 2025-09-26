from flask import request, jsonify

def log_request_info():
    app.logger.info('Request Headers: %s', request.headers)
    app.logger.info('Request Body: %s', request.get_json())

def handle_api_errors(error):
    response = jsonify({'error': str(error)})
    response.status_code = 400
    return response

def add_middleware(app):
    app.before_request(log_request_info)
    app.errorhandler(Exception)(handle_api_errors)