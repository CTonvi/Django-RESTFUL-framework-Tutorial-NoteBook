def jwt_response_payload_handler(token, user=None, request=None, role=None):

    if user.first_name:
        name = user.first_name
    else:
        name = user.username
    
    return {
        'authenticated': 'true',
        'username': user.username,
        'token': token,
    }