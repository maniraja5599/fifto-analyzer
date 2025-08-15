from django import template
from datetime import datetime

register = template.Library()

@register.filter
def time_12hour(value):
    """Convert 24-hour time string to 12-hour format with AM/PM."""
    if not value:
        return value
    
    try:
        # If it's already in a complete datetime format, try parsing it
        if len(str(value)) > 5:  # More than just HH:MM format
            if ' AM' in str(value) or ' PM' in str(value):
                return value  # Already in 12-hour format
            
            # Try parsing full datetime
            try:
                dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
                return dt.strftime('%I:%M %p')
            except:
                pass
        
        # Handle HH:MM format (from HTML time inputs)
        time_str = str(value)
        if ':' in time_str:
            try:
                # Parse as time only
                dt = datetime.strptime(time_str, '%H:%M')
                return dt.strftime('%I:%M %p')
            except ValueError:
                # Try with seconds
                try:
                    dt = datetime.strptime(time_str, '%H:%M:%S')
                    return dt.strftime('%I:%M %p')
                except ValueError:
                    pass
        
        # If all else fails, return original value
        return value
        
    except (ValueError, TypeError):
        return value

@register.filter
def datetime_12hour(value):
    """Convert datetime string to 12-hour format with AM/PM."""
    if not value:
        return value
    
    try:
        # If it's already in 12-hour format, return as is
        if ' AM' in str(value) or ' PM' in str(value):
            return value
            
        # Try parsing various datetime formats
        dt = None
        
        # Try different formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%H:%M:%S',
            '%H:%M'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(str(value), fmt)
                break
            except ValueError:
                continue
        
        if dt:
            if fmt in ['%H:%M:%S', '%H:%M']:
                # Time only
                return dt.strftime('%I:%M %p')
            else:
                # Full datetime
                return dt.strftime('%Y-%m-%d %I:%M %p')
        
        # If parsing failed, return original
        return value
        
    except (ValueError, TypeError):
        return value
