def func_sns_send_mobile_message(*, client_sns: any, mobile: str, message: str) -> None:
    """Send a mobile SMS using AWS SNS."""
    client_sns.publish(PhoneNumber=mobile, Message=message)
    return None

def func_sns_send_mobile_message_template(*, client_sns: any, mobile: str, message: str, template_id: str, entity_id: str, sender_id: str) -> None:
    """Send a mobile SMS using AWS SNS with specific template and attributes."""
    client_sns.publish(PhoneNumber=mobile, Message=message, MessageAttributes={"AWS.SNS.SMS.SenderID": {"DataType": "String", "StringValue": sender_id}, "AWS.MM.SMS.TemplateId": {"DataType": "String", "StringValue": template_id}, "AWS.MM.SMS.EntityId": {"DataType": "String", "StringValue": entity_id}, "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"}})
    return None
