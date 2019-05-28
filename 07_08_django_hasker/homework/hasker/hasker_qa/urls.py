from django.urls import path

from . import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('ask/', views.AskView.as_view(), name='ask'),
    path('question/<int:pk>/', views.QuestionView.as_view(), name='question'),
    path('question/<int:pk>/vote/', views.QuestionVoteView.as_view(), name='question_vote'),
    path('answer/', views.AnswerView.as_view(), name='answer'),
    path('answer/<int:pk>/vote/', views.AnswerVoteView.as_view(), name='answer_vote'),
    path('answer/<int:pk>/mark/', views.AnswerMarkView.as_view(), name='answer_mark'),
]
