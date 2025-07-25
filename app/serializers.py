
import re
from rest_framework import serializers
from .models import User, ProgramReview

class UserSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'photo_url']

    def get_photo_url(self, obj):
        url = obj.photo_url
        if not url:
            return ''
        request = self.context.get('request')
        if url.startswith('http://') or url.startswith('https://'):
            return url
        if request:
            return request.build_absolute_uri(url)
        # fallback: hardcode localhost for dev
        return f"http://localhost:8000{url}" if url.startswith('/') else url

class SignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
            'phone': {'min_length': 10, 'max_length': 10}
        }

    def validate(self, data):
        password = data.get('password')
        errors = []
        if password is not None:
            if len(password) < 6:
                errors.append('Password must be at least 6 characters long.')
            if not re.search(r'[A-Z]', password):
                errors.append('Password must contain at least one uppercase letter.')
            if not re.search(r'[a-z]', password):
                errors.append('Password must contain at least one lowercase letter.')
            if not re.search(r'\d', password):
                errors.append('Password must contain at least one number.')
            if not re.search(r'[^A-Za-z0-9]', password):
                errors.append('Password must contain at least one special character.')
            if errors:
                raise serializers.ValidationError({'password': errors})
        return data

class ProgramReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgramReview
        fields = ['id', 'program', 'name', 'review', 'rating', 'created_at']
