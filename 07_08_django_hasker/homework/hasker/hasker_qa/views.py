import re

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, F, Q
from django.db.models.functions import Coalesce
from django.http import HttpRequest, QueryDict
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import CreateView, ListView, DetailView
from django.views.generic.detail import BaseDetailView

from hasker_accounts.models import User
from hasker_qa.forms import AskForm, QuestionGetParamsForm, AnswerForm, VoteForm
from hasker_qa.models import Question, Answer, Tag

question_query_set = Question.objects. \
    annotate(votes_sum=Coalesce(Sum(F('votes__sign')), 0)). \
    select_related('author')


def common_context(context: dict, form_url: str = ''):
    context.update({
        'trending_questions': IndexView.queryset.order_by('-votes_sum'),
    }
    )
    if form_url:
        context.update({
            'form_url': reverse(form_url),
        }
        )


class IndexView(ListView):
    model = Question
    ordering = '-creation_date'
    template_name = 'hasker_qa/index.html'
    queryset = question_query_set
    context_object_name = 'questions'
    paginate_by = 20

    tag_regex = re.compile(r"tag:(?P<name>\w+?)$")

    def get_text_search(self, query):
        """Perfom a text search"""
        self.q_text = ''
        if self.form.is_valid():
            q_text = self.form.cleaned_data['q']
            self.q_text = q_text
            search = self.tag_regex.search(q_text)
            if search:
                tag_name = search.group('name')
                return query.filter(tags__name=tag_name)
            query = query.filter(Q(title__icontains=q_text) | Q(text__icontains=q_text))
        return query

    def get_queryset(self):
        self.form = form = QuestionGetParamsForm(self.request.GET)
        query = super().get_queryset()
        return self.get_text_search(query)

    def get_ordering(self):
        form = self.form
        if form.is_valid() and form.cleaned_data['ordering']:
            return '-votes_sum'
        return self.ordering

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=None, **kwargs)
        # Prepare get data for build with pagination
        qdict = QueryDict('', mutable=True)
        qdict.update(self.form.cleaned_data)
        self.request.GET = qdict
        context.update({
            'q_text': self.q_text,
        })
        return context


class AskView(LoginRequiredMixin, CreateView):
    template_name = 'hasker_qa/ask.html'
    form_class = AskForm

    def set_tags(self, tags_list):
        """Set tags for a question"""
        for tag_name in tags_list:
            tag, status = Tag.objects.get_or_create(name=tag_name)
            self.object.tags.add(tag)

    def form_valid(self, form):
        obj: Question = form.instance
        obj.author = self.request.user
        response = super().form_valid(form)

        self.set_tags(form.cleaned_data['tags'])
        return response

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=None, **kwargs)
        common_context(context, 'ask')
        return context

    def get_success_url(self):
        return self.object.get_absolute_url()


class QuestionView(DetailView):
    model = Question
    context_object_name = 'question'
    template_name = 'hasker_qa/question.html'
    queryset = question_query_set

    def set_vote_status(self, obj):
        sign = None
        sign_obj = obj.votes.filter(user=self.request.user.id).first()
        if sign_obj:
            sign = sign_obj.sign
        setattr(obj, 'vote_status', sign)

    def get_context_data(self, **kwargs):
        answers_list = []
        context = super().get_context_data(**kwargs)
        obj: Question = self.object
        self.set_vote_status(obj)

        answers = obj.answers.select_related('author'). \
            annotate(votes_sum=Coalesce(Sum(F('votes__sign')), 0)). \
            order_by('-votes_sum', '-creation_date')
        for answer in answers:
            # status for answer votes
            self.set_vote_status(answer)
            answers_list.append(answer)

        context.update({
            'answers': answers_list
        })
        common_context(context)
        return context


class AnswerView(LoginRequiredMixin, CreateView):
    form_class = AnswerForm
    http_method_names = ['post']

    def form_valid(self, form):
        obj: Answer = form.instance
        obj.author = self.request.user
        result: Answer = super().form_valid(form)
        if not settings.DEBUG:
            obj.question.email_author()
        return result


class ChangeAbstractView(LoginRequiredMixin, BaseDetailView):
    http_method_names = ['post']


class AnswerMarkView(ChangeAbstractView):
    """Mark right answer"""
    model = Answer

    def post(self, request, *args, **kwargs):
        answer: Answer = self.get_object()
        if answer.question.author == request.user:
            current_correct_answer: Answer = answer.question.answers.filter(correct_answer=True).first()
            if current_correct_answer:
                current_correct_answer.correct_answer = None
                current_correct_answer.save()
            # Check correct answer only if it different from current
            if current_correct_answer != answer:
                answer.correct_answer = True
                answer.save()
        return redirect(answer.get_absolute_url())


class VoteAbstractView(ChangeAbstractView):
    @staticmethod
    def change_vote(request: HttpRequest, obj, author):
        """Set vote if old not exist or change it or delete it."""
        current_user: User = request.user
        form = VoteForm(request.POST)
        if form.is_valid() and author != current_user:
            sign = form.cleaned_data['sign']
            existed_vote = obj.votes.filter(user=current_user).first()
            if existed_vote:
                existed_vote.delete()
            if existed_vote is None or existed_vote.sign != sign:
                obj.votes.model.objects.create(user=current_user, entity=obj, sign=sign)
        return redirect(obj.get_absolute_url())


class AnswerVoteView(VoteAbstractView):
    """Vote for answer"""
    model = Answer

    def post(self, request, *args, **kwargs):
        obj: Answer = self.get_object()
        question_author = obj.question.author
        return self.change_vote(request, obj, question_author)


class QuestionVoteView(VoteAbstractView):
    """Vote for Question"""
    model = Question

    def post(self, request, *args, **kwargs):
        obj: Question = self.get_object()
        question_author = obj.author
        return self.change_vote(request, obj, question_author)
