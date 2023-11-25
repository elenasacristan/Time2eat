import os
'''
env is where I have my environmental variables and it is only used to run my code locally, in production is 
commented out
'''
# import env
import json
from flask import Flask, render_template, request, url_for, redirect, session, flash
from flask_pymongo import PyMongo, DESCENDING
from bson.objectid import ObjectId
from bson import json_util
from bson.json_util import dumps
from datetime import datetime
import bcrypt

# create an instance of Flask
app = Flask(__name__)

'''
In development the environmental variables are saved on the env.py and in production the environmental variables are 
saved on the Config Var in Heroku
'''
app.config["MONGO_DBNAME"] = os.environ.get('MONGO_DBNAME')
app.config['MONGO_URI'] = os.environ.get('MONGODB_URI')

# we create an instance of Mongo
mongo = PyMongo(app)

# secret key needed to create session cookies
app.secret_key = os.environ.get('SECRET_KEY')

#function used to convert strings separated by '\n' to arrays
def string_to_array(string):
    array = string.split("\n")
    return array
    
'''
Landing page for the website for new users. I learn how to create the login/register functionality by watching this 
tutorial https://www.youtube.com/watch?v=vVx1737auSE
 '''
@app.route('/')
def index():
    # if the cookie for the user already exist the login page is skipped
    if "username" in session:
        return redirect(url_for('get_recipes'))
    
    return render_template('login.html', title="Login")


@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        users = mongo.db.Users
        user_login = users.find_one({'author':request.form['username'].capitalize()})

        if user_login:
            if bcrypt.hashpw(request.form['password'].encode('utf-8'), user_login['password']) == user_login['password']:
                session["username"] = request.form["username"].capitalize()
                return redirect(url_for('get_recipes'))
        
        flash('The login details are not correct')
        return render_template('login.html',  title="Login")

    return render_template('login.html',  title="Login")


@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        users = mongo.db.Users
        user_exists = users.find_one({'author':request.form['username'].capitalize()})

        if user_exists is None:
            hashpass = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())
            users.insert({'author':request.form['username'].capitalize(), 'password':hashpass})
            session['username'] = request.form['username'].capitalize()
            return redirect(url_for('get_recipes'))

        flash('That username already exists, please choose a different one.')
        return render_template('register.html', title="Register")

    return render_template('register.html', title="Register")


'''
Home page, the recipes are sorted by votes and after by views. The most voted will 
be on the top one of the carousel and the it will be in descending order if you move to the right
'''
@app.route('/get_recipes')
def get_recipes():
    recipes = mongo.db.Recipes.find().sort([("upvotes",DESCENDING), ("views",DESCENDING)])
    return render_template('get_recipes.html',
                            title="View recipes", 
                            username=session['username'], 
                            recipes = recipes, 
                            categories = mongo.db.Categories.find(), 
                            cuisines=mongo.db.Cuisines.find(), 
                            difficulty=mongo.db.Difficulty.find(), 
                            allergens=mongo.db.Allergens.find(), 
                            recipes_count=recipes.count())
  

#search functionality in the home page
@app.route('/search', methods=['POST'])
def search():
    #we get the word to find from the search box    
    text_to_find = request.form["text_to_find"]
        
    #we create a text index for all the text fields   
    mongo.db.Recipes.create_index([("$**", 'text')])

    #Search result sorted by upvotes descending and after by number of views descending    
    recipes = mongo.db.Recipes.find({"$text":{"$search": text_to_find}}).sort([("upvotes",DESCENDING),("views",DESCENDING)])
            
    # send recipes to page
    return render_template('get_recipes.html',
                            title="View recipes", 
                            username=session['username'], 
                            recipes = recipes, 
                            categories = mongo.db.Categories.find(), 
                            cuisines=mongo.db.Cuisines.find(), 
                            difficulty=mongo.db.Difficulty.find(), 
                            allergens=mongo.db.Allergens.find(), 
                            recipes_count=recipes.count()) 
         

'''
Create different query depending on if a cuisine, difficulty or category has been selected or not in the 
dropdown menu or checkboxes. I nothing has been selected we will display all the options available, 
if some options have been selected then we will filter by the options selected
'''
def query_needed(recipes, field):
    if request.form.getlist(field) != []:
        return {field:{ "$in": request.form.getlist(field)}}
    else:
        return {field:{ "$in": recipes.distinct(field)}}


#filter section in home page
@app.route('/filter_recipes', methods = ['GET', 'POST'])
def filter_recipes():
    
    recipes = mongo.db.Recipes.find()
    
    # create different query depending is the user selects "only_mine" or not"
    if request.form.get('only_mine') == 'only_mine':
        query_author = {"author": session['username'] }
    else:
        query_author = {"author": { "$in": recipes.distinct('author') } }
    
    # get the right query depending on if any options have been selected or nothing has been selected
    query_cuisine = query_needed(recipes,'cuisine');
    query_difficulty = query_needed(recipes,'difficulty');
    query_categories = query_needed(recipes,'category');

    # from the checkboxes in the filter section get the list of allergens to exclude 
    allergens_to_remove = request.form.getlist('allergens')
    
    #query to show all the recipes that DON'T contain the allergens selected
    query_allergens = {"allergens": { "$nin": allergens_to_remove } }
   
    #query to find the recipes with the filters used - ordered by views and then by votes descending
    recipes = mongo.db.Recipes.find({"$and":
                                    [query_author,
                                    query_difficulty,
                                    query_cuisine,
                                    query_allergens, 
                                    query_categories]}).sort([("upvotes",DESCENDING), ("views",DESCENDING)])
    recipes_count = recipes.count()

    return render_template('get_recipes.html', 
                            title="View recipes", 
                            username=session['username'], 
                            recipes = recipes, 
                            categories = mongo.db.Categories.find(), 
                            cuisines=mongo.db.Cuisines.find(), 
                            difficulty=mongo.db.Difficulty.find(), 
                            allergens=mongo.db.Allergens.find(), 
                            recipes_count=recipes_count)
   

#route to the tips page
@app.route('/tips')
def tips():
    return render_template('tips.html', title="Tips")


# add new recipe
@app.route('/add_recipe')
def add_recipe():
    return render_template('add_recipe.html', 
                            title="Add recipe", 
                            categories = mongo.db.Categories.find(), 
                            cuisines=mongo.db.Cuisines.find(), 
                            difficulty=mongo.db.Difficulty.find(), 
                            allergens=mongo.db.Allergens.find())


''' 
funtion to insert into the database the new recipe I also learn how to save and retrieve files in MongoDB by watching
the following tutorial: https://www.youtube.com/watch?v=DsgAuceHha4
'''
@app.route('/insert_recipe', methods=['POST'])
def insert_recipe():
    if 'recipe_image' in request.files:
        recipe_image = request.files['recipe_image']
        if recipe_image != "":
            mongo.save_file(recipe_image.filename, recipe_image)
        
        if request.form['calories']:
            calories = request.form['calories']
        else:
            calories = "Not specified"

        mongo.db.Recipes.insert({
                'recipe_name':request.form['recipe_name'].capitalize(),
                'instructions':string_to_array(request.form['instructions']),
                'serves':request.form['serves'],
                'calories':calories,
                'difficulty':request.form['difficulty'],
                'cooking_time':request.form['cooking_time'],
                'cuisine':request.form['cuisine'],
                'allergens':request.form.getlist('allergens'),
                'ingredients':string_to_array(request.form['ingredients']),
                'recipe_image':recipe_image.filename,
                'author':session['username'],
                'upvotes':0,
                'date':datetime.now().strftime("%d/%m/%Y"),
                'category':request.form['category']
            })
    return redirect(url_for('get_recipes'))


# function to see a recipe after clicking on its image or "view" link
@app.route('/view_recipe/<recipe_id>')
def view_recipe(recipe_id):
    #we increment the number of views everytime a recipe is seen
    mongo.db.Recipes.update_one({"_id":ObjectId(recipe_id)}, {'$inc': {'views': 1}})
    
    return render_template('view_recipe.html', 
                            recipe = mongo.db.Recipes.find_one({"_id":ObjectId(recipe_id)}), username = session['username'])


'''
function to vote the recipes.
The recipe author is not allowed to vote for his recipes. Each user is only allowed to vote once for each recipe
'''
@app.route('/view_recipe/vote/<recipe_id>')
def vote(recipe_id):
    users = mongo.db.Users
    
    already_voted = users.find_one({"$and":[{"author":session['username']},{'votes':recipe_id}]})

    if already_voted is None:
        mongo.db.Recipes.update_one({"_id":ObjectId(recipe_id)}, {'$inc': {'upvotes': 1}})
        users.update_one({"author":session['username']},{"$push":{"votes":recipe_id}})
    else:
        flash("You have already voted for this recipe")
        
    return redirect(url_for("view_recipe", recipe_id=recipe_id))


# Edit recipe view
@app.route('/edit_recipe/<recipe_id>')
def edit_recipe(recipe_id):
    recipe = mongo.db.Recipes.find_one({"_id":ObjectId(recipe_id)})
    list_ingredients = '\n'.join(recipe['ingredients'])
    list_allergens = '\n'.join(recipe['allergens'])
    list_instructions = '\n'.join(recipe['instructions'])

    return render_template('edit_recipe.html', 
                            recipe=recipe, 
                            categories=mongo.db.Categories.find(), 
                            cuisines=mongo.db.Cuisines.find(), 
                            difficulty=mongo.db.Difficulty.find(), 
                            list_ingredients=list_ingredients, 
                            list_allergens=list_allergens,
                            list_instructions=list_instructions, 
                            allergens=mongo.db.Allergens.find())


'''
Funcion to update recipes. In the video below I learned how to upload images into MongoDB:
https://www.youtube.com/watch?v=DsgAuceHha4 
'''
@app.route('/update_recipe/<recipe_id>' , methods=['GET', 'POST'])
def update_recipe(recipe_id):
    recipes = mongo.db.Recipes
    recipe = mongo.db.Recipes.find({"_id":ObjectId(recipe_id)})
    if 'recipe_image' in request.files:
            recipe_image = request.files['recipe_image']
            mongo.save_file(recipe_image.filename, recipe_image)
            
            if request.form['calories']:
                calories = request.form['calories']
            else:
                calories = "Not specified"

            recipes.update({"_id":ObjectId(recipe_id)},{ "$set":
                {
                    'recipe_name':request.form['recipe_name'].capitalize(),
                    'instructions':string_to_array(request.form['instructions']),
                    'serves':request.form['serves'],
                    'calories':calories,
                    'difficulty':request.form['difficulty'],
                    'cooking_time':request.form['cooking_time'],
                    'cuisine':request.form['cuisine'],
                    'allergens':request.form.getlist('allergens'),
                    'ingredients':string_to_array(request.form['ingredients']),
                    'category':request.form['category']      
                }})

            if recipe_image.filename != "":   
                recipes.update({"_id":ObjectId(recipe_id)},{ "$set":{'recipe_image':recipe_image.filename,}})       
    
    return redirect(url_for("view_recipe", recipe_id=recipe_id))


@app.route('/img_uploads/<filename>')
def img_uploads(filename):
    return mongo.send_file(filename)


# function to remove a recipe (only the author can remove a recipe)
@app.route('/delete_recipe/<recipe_id>')
def delete_recipe(recipe_id):
    mongo.db.Recipes.remove({"_id":ObjectId(recipe_id)})
    return redirect(url_for('get_recipes'))


# function to see and insert new categories or cuisines
@app.route('/manage_categories')
def manage_categories():
    recipes = mongo.db.Recipes.find()
    categories = mongo.db.Categories.find()
    cuisines = mongo.db.Cuisines.find()
    category_object=[]
    cuisine_object=[]

    for category in categories:
	    count_recipes_category = mongo.db.Recipes.find({'category':category['category']}).count()
	    category_object.append({"category_id" : category['_id'] ,
                                "category" : category['category'], 
                                "count_recipes_category" : count_recipes_category})   
   
    #sort categories by number of recipes in descending order
    category_object_sorted = sorted(category_object, key=lambda x: x['count_recipes_category'], reverse=True)

    for cuisine in cuisines:
	    count_recipes_cuisine = mongo.db.Recipes.find({'cuisine':cuisine['cuisine']}).count()
	    cuisine_object.append({"cuisine_id" : cuisine['_id'], 
                                "cuisine" : cuisine['cuisine'], 
                                "count_recipes_cuisine" : count_recipes_cuisine} )
   
    #sort cuisines by number of recipes in descending order
    cuisine_object_sorted = sorted(cuisine_object, key=lambda x: x['count_recipes_cuisine'], reverse=True)

    return render_template('manage_categories.html', 
                            title="Type of meals / cuisines", 
                            categories = category_object_sorted, 
                            cuisines = cuisine_object_sorted)
    

# function to insert a new category into the database
@app.route('/insert_category', methods=['POST'])
def insert_category():
    categories = mongo.db.Categories 
    category_form = request.form['category'].capitalize()
    category_exists = categories.find_one({'category':category_form})

    if category_exists is None:    
        categories.insert_one({
            'category':request.form['category'].capitalize()
            })
        return redirect(url_for('manage_categories'))
    else:
        flash('That type of meal already exists')
        return redirect(url_for('manage_categories'))


# function to insert a new cuisine into the database
@app.route('/insert_cuisine', methods=['POST'])
def insert_cuisine():
    cuisines = mongo.db.Cuisines  
    cuisine_form = request.form['cuisine'].capitalize()
    cuisine_exists = cuisines.find_one({'cuisine':cuisine_form})

    if cuisine_exists is None:    
        cuisines.insert_one({
            'cuisine':request.form['cuisine'].capitalize()
            })
        return redirect(url_for('manage_categories'))
    else:
        flash('That cuisine already exists')
        return redirect(url_for('manage_categories'))


@app.route('/delete_category/<category_id>')
def delete_category(category_id):
    mongo.db.Categories.remove({"_id":ObjectId(category_id)})
    return redirect(url_for('manage_categories'))


@app.route('/delete_cuisine/<cuisine_id>')
def delete_cuisine(cuisine_id):
    mongo.db.Cuisines.remove({"_id":ObjectId(cuisine_id)})
    return redirect(url_for('manage_categories'))
   
'''
we use this route to retrieve all the recipes from the database in json format. The following tutorial help me 
to create this function: http://adilmoujahid.com/posts/2015/01/interactive-data-visualization-d3-dc-python-mongodb/
'''
@app.route("/data_recipes")
def data():
    recipes = mongo.db.Recipes.find()
    json_recipes = []

    for recipe in recipes:
        json_recipes.append(recipe)
    json_recipes = json.dumps(json_recipes, default=json_util.default, indent= 4, sort_keys=True)
         
    return json_recipes
    
# Statistics view
@app.route("/statistics")
def statistics():
    return render_template('statistics.html', title="Dashboard")


'''
function to log out / clear cookie
I understood how to log out a user by watching the following tutorial: 
# https://www.tutorialspoint.com/flask/flask_sessions.htm
'''
@app.route('/logout')
def logout():
 # remove the username from the session if it is there
    session.pop('username', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host=os.environ.get('IP'), port=int(os.environ.get('PORT')))
