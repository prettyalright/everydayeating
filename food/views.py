from django.template import Context, loader
from food.models import Ingredient
from django.http import HttpResponse

def ingredient_index(request):
    ingredient_list = Ingredient.objects.all().order_by('name')[:10]
    t = loader.get_template('food/ingredient_index.html')
    c = Context({
        'ingredient_list': ingredient_list,
    })
    return HttpResponse(t.render(c))


#    output = ', '.join([i.name for i in ingredient_list])
#    return HttpResponse(output)

#    return HttpResponse("Hello, world. You're at the ingredients index.")

def ingredient_detail(request, ingredient_id):
    return HttpResponse("You're looking at ingredient %s." % ingredient_id)

def ingredient_add(request):
    return HttpResponse("Hello, world. You're trying to add a new ingredient.")

