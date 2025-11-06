from django import forms
from .models import Questions
import ast

class QuestionsForm(forms.ModelForm):
    options = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        help_text="Enter options as a Python list, e.g., ['Option A', 'Option B', 'Option C']"
    )

    class Meta:
        model = Questions
        fields = ['subject', 'question_text', 'options', 'correct_option', 'explain']

    def clean_options(self):
        data = self.cleaned_data['options']

        try:
            # Use ast.literal_eval for safe parsing of list input
            options_list = ast.literal_eval(data)

            if not isinstance(options_list, list):
                raise ValueError("Not a list")

            # Optionally strip whitespace from items
            options_list = [opt.strip() for opt in options_list if isinstance(opt, str)]

            if len(options_list) < 2:
                raise ValueError("Must provide at least 2 options.")

        except Exception as e:
            raise forms.ValidationError("Invalid format. Use: ['Option A', 'Option B']")

        return options_list

    def clean(self):
        cleaned_data = super().clean()
        options = cleaned_data.get('options')
        correct = cleaned_data.get('correct_option')

        if options and correct and correct not in options:
            raise forms.ValidationError("Correct option must match one of the provided options.")

        return cleaned_data
