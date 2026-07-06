{% extends 'base.html' %}{% block content %}<h1>Portfolio</h1><pre>{{ portfolio | tojson(indent=2) }}</pre>{% endblock %}
