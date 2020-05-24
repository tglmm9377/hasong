from django.contrib.auth.decorators import login_required

class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls,**initkwagrs):
        view = super(LoginRequiredMixin, cls).as_view(**initkwagrs)
        return login_required(view)
