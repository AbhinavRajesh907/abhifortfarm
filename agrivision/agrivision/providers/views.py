from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, TemplateView
from .models import ProviderProfile, ProviderRequest
from .forms import ProviderProfileForm, ProviderRequestForm

class ProviderDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'providers/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile, created = ProviderProfile.objects.get_or_create(user=self.request.user)
        context['profile'] = profile
        context['requests'] = profile.requests.all().order_by('-created_at')
        return context

class ProviderProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = ProviderProfile
    form_class = ProviderProfileForm
    template_name = 'providers/profile_form.html'
    success_url = reverse_lazy('providers:dashboard')

    def get_object(self, queryset=None):
        profile, created = ProviderProfile.objects.get_or_create(user=self.request.user)
        return profile

class ProviderRequestCreateView(LoginRequiredMixin, CreateView):
    model = ProviderRequest
    form_class = ProviderRequestForm
    template_name = 'providers/request_form.html'
    success_url = reverse_lazy('providers:dashboard')

    def form_valid(self, form):
        profile, created = ProviderProfile.objects.get_or_create(user=self.request.user)
        form.instance.provider = profile
        return super().form_valid(form)
