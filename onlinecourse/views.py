from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import generic

# <HINT> Import any new Models here
from .models import Course, Enrollment

if TYPE_CHECKING:
    from django.db.models import BaseManager

# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request: HttpRequest) -> HttpResponse:
    context = {}
    if request.method == "GET":
        return render(request, "onlinecourse/user_registration_bootstrap.html", context)
    if request.method == "POST":
        # Check if user exists
        username = request.POST["username"]
        password = request.POST["psw"]
        first_name = request.POST["firstname"]
        last_name = request.POST["lastname"]
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:  # noqa: E722
            logger.exception("New user")
        if not user_exist:
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                password=password,
            )
            login(request, user)
            return redirect("onlinecourse:index")
        context["message"] = "User already exists."
        return render(request, "onlinecourse/user_registration_bootstrap.html", context)
    return HttpResponse("Method not allowed", status=405)


def login_request(request: HttpRequest) -> HttpResponse:
    context = {}
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["psw"]
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("onlinecourse:index")
        context["message"] = "Invalid username or password."
        return render(request, "onlinecourse/user_login_bootstrap.html", context)
    return render(request, "onlinecourse/user_login_bootstrap.html", context)


def logout_request(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("onlinecourse:index")


def check_if_enrolled(user: User, course: Course) -> bool:
    is_enrolled = False
    if user.id is not None:  # pyright: ignore[reportAttributeAccessIssue]
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = "onlinecourse/course_list_bootstrap.html"
    context_object_name = "course_list"

    def get_queryset(self) -> BaseManager[Course]:
        user = self.request.user
        courses = Course.objects.order_by("-total_enrollment")[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)  # pyright: ignore[reportArgumentType]
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = "onlinecourse/course_detail_bootstrap.html"


def enroll(request: HttpRequest, course_id: int) -> HttpResponse:
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)  # pyright: ignore[reportArgumentType]
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode="honor")
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname="onlinecourse:course_details", args=(course.id,)))  # pyright: ignore[reportAttributeAccessIssue]


# <HINT> Create a submit view to create an exam submission record for a course enrollment,
# you may implement it based on following logic:
# Get user and course object, then get the associated enrollment object created when the user
# enrolled the course
# Create a submission object referring to the enrollment
# Collect the selected choices from exam form
# Add each selected choice object to the submission object
# Redirect to show_exam_result with the submission id
# def submit(request, course_id):


# An example method to collect the selected choices from the exam form from the request object
def extract_answers(request: HttpRequest) -> list[int]:
    submitted_answers = []
    for key in request.POST:
        if key.startswith("choice"):
            value = request.POST[key]
            choice_id = int(value)
            submitted_answers.append(choice_id)
    return submitted_answers


# <HINT> Create an exam result view to check if learner passed exam and show their question results
# and result for each question,
# you may implement it based on the following logic:
# Get course and submission based on their ids
# Get the selected choice ids from the submission record
# For each selected choice, check if it is a correct answer or not
# Calculate the total score
# def show_exam_result(request, course_id, submission_id):
