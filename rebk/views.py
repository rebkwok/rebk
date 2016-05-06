from django.shortcuts import render


def permission_denied(request):
    return render(request, 'permission_denied.html')
