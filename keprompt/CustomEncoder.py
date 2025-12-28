import json
from decimal import Decimal
from datetime import datetime, date


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        # Handle Peewee Model instances
        if hasattr(obj, '__data__'):  # Peewee models have __data__ attribute
            # Get the raw data dictionary and recursively process it
            data = obj.__data__
            result = {}
            for key, value in data.items():
                # Recursively handle nested objects
                if isinstance(value, Decimal):
                    result[key] = float(value)
                elif isinstance(value, (datetime, date)):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
            return result
        # Handle Decimal (used in cost fields)
        if isinstance(obj, Decimal):
            return float(obj)
        # Handle datetime objects
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        # Fallback: try __dict__
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        return json.JSONEncoder.default(self, obj)
