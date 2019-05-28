from django import forms

from hasker_qa.models import Question, Answer, AbstractVoteUser


class AskForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ('title', 'text')

    tags = forms.CharField(help_text='Enter tags separated by space')

    def clean_tags(self):
        tags_list = self.cleaned_data['tags'].split(' ')
        if len(tags_list) > 3:
            raise forms.ValidationError("Tags more than 3!")

        return tags_list


class QuestionGetParamsForm(forms.Form):
    ORDERING_CHOICES = (
        ('votes_sum', ''),
    )
    ordering = forms.ChoiceField(choices=ORDERING_CHOICES, required=False)
    q = forms.CharField()


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ('text', 'question')

    question = forms.HiddenInput()


class VoteForm(forms.Form):
    sign = forms.ChoiceField(choices=AbstractVoteUser.SIGN_CHOICES, required=True)

    def clean_sign(self):
        return int(self.cleaned_data['sign'])
