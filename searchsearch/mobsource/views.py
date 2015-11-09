from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
import requests
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django import forms
from .models import Language, User, Query, QueryMotive, QueryComment, QueryResult, REQD_RESULTS, ndcg
from django.db import IntegrityError


def index(request):
    return render(request, 'mobsource/index.html')


class SearchForm(forms.Form):

    MAX_QUERY_LENGTH=255

    def __init__(self, *args, **kwargs):
        super(forms.Form, self).__init__(*args, **kwargs)
        for i in range(REQD_RESULTS):
            self.fields['result_id_' + str(i)] = forms.CharField(required=True, widget=forms.HiddenInput(attrs={ 'class' : 'euro-id'}))
            self.fields['result_rating_' + str(i)] = forms.IntegerField(required=True, widget=forms.HiddenInput(attrs={ 'class' : 'rel-rating'}))

    test_query = forms.CharField(label="Query*", max_length=MAX_QUERY_LENGTH)
    lang_choice = [('', '------------')]
    for row in Language.objects.all():
        lang_choice.append((row.language, row.language))
    languages = forms.ChoiceField(label="What language is this?*", choices=lang_choice, widget=forms.Select(attrs={ 'id' : 'lang-selector'}), initial='')
    query_motive = forms.CharField(required=False, label="Why do you like this query? What are you looking for, and why is it interesting to you?", widget=forms.Textarea)
    query_comment = forms.CharField(required=False, label="Is there anything to note about this result set? Is there anything missing you were expecting to see? Anything you weren't expecting, or didn't want, to see?", widget=forms.Textarea)
    previous_query = forms.CharField(required=False, max_length=MAX_QUERY_LENGTH, widget=forms.HiddenInput(attrs={ "id" : "prev-query" }))
    duplicate_key = forms.CharField(required=False, max_length=1, widget=forms.HiddenInput(attrs={"id":"duplicate-key"}))
    logging_out = forms.CharField(required=False, max_length=1, widget=forms.HiddenInput(attrs={ "id" : "logging-out"}))

@login_required()
def searchform(request):
    if request.method == "POST":
        search_form = SearchForm(request.POST)
        if(search_form.is_valid()):
            query = search_form.cleaned_data['test_query']
            lang = search_form.cleaned_data['languages']
            motive = search_form.cleaned_data['query_motive']
            comment = search_form.cleaned_data['query_comment']
            source = User.objects.get(id=request.user.id)
            l = Language.objects.get(language=lang)
            q = Query(query_text=query, language=l, source=source)
            try:
                q.save()
            except IntegrityError:
                return render(request, 'mobsource/searchform.html', { 'form':SearchForm(initial={'test_query':query, 'languages':lang, 'query_motive':motive, 'query_comment':comment, 'duplicate_key': 'T'}) })
            counter = 0
            query_scores = []
            while counter < REQD_RESULTS:
                id_field = 'result_id_' + str(counter)
                rating_field = 'result_rating_' + str(counter)
                item_id = search_form.cleaned_data[id_field]
                item_rating = search_form.cleaned_data[rating_field]
                query_scores.append(item_rating);
                qr = QueryResult(query=q, position=counter, europeana_id=item_id, rating=item_rating)
                qr.save()
                counter += 1
            score = ndcg(query_scores)
            q.ndcg = score
            q.save()
            if motive != '':
                qm = QueryMotive(motive_text=motive, query=q)
                qm.save()
            if comment != '':
                qc = QueryComment(comment_text=comment, query=q)
                qc.save()
            if('quit' in request.POST):
                return HttpResponseRedirect("/accounts/logout")
            else:
                return render(request, 'mobsource/searchform.html', { 'form':SearchForm(initial={ 'duplicate_key' : 'F' }) })
        elif 'quit' in request.POST:
            search_form.add_error("logging_out", "logout")
            return render(request, 'mobsource/searchform.html', { 'form':search_form })
    else:
        search_form = SearchForm()

    return render(request, 'mobsource/searchform.html', {'form':search_form})

def do_query(search_obj):

    qry = search_obj.GET['query']
    url = "http://europeana.eu/api/v2/search.json"
    data = {
            'wskey': 'fwejAubet',
            'query':qry,
            'rows':10,
            'profile':'rich'
    }
    response = requests.get(url, params=data)
    as_json = response.json()
    duplicate_test = Query.objects.filter(query_text=qry).count() > 0
    if(duplicate_test): as_json['duplicate']=True
    return JsonResponse(as_json)

