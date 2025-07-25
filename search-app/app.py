from datetime import timedelta
import traceback
import psycopg2
from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.options import (ClusterOptions, ClusterTimeoutOptions, QueryOptions)
from flask import Flask, render_template, url_for, request, session
from datetime import datetime
from Cache import LRUCache
import flask

app = Flask(__name__)

# cache object
cache = LRUCache(capacity=4)

# Couchbase connection
cluster = Cluster.connect(
    "couchbases://cb.a7ctqokyo0vlpzkl.cloud.couchbase.com",
    ClusterOptions(PasswordAuthenticator("Tanvi", "Rutgers@1405")))
bucket = cluster.bucket("Twitter_Dataset")
collection = bucket.default_collection()

# PostgreSQL connection
rds_endpoint = 'mydb-1.c7cwkme4c32f.us-east-2.rds.amazonaws.com'
db_username = "postgres1"
db_password = "pass#111"
pg_conn = psycopg2.connect(
    dbname='initial_db',
    user=db_username,
    password=db_password,
    host=rds_endpoint,
    port='5433'
)
pg_cursor = pg_conn.cursor()


@app.route('/')
def home():
    return render_template('index.html')


@app.route("/select", methods=['GET', 'POST'])
def get_options():
    
    if request.method == 'POST':
        global option
        option = request.form['options']
        
        if option == "username":
            result = "username"
            
        elif option == "text":
            result = "text"
        
        elif option == "hashtags":
            result = "hashtags"
        
        elif option == "date":
            result = "date"
        
        elif option == "lang":
            result = "lang"
            
        elif option == "users" or option == "tweets":
            result = "top10"
            
            if option == "tweets":
                start_time = datetime.now()
                top_10_tweets = get_top_10_tweets()
                end_time = datetime.now()
                time = (end_time - start_time).total_seconds()
                
                count = len(top_10_tweets)
            
            elif option == "users":
                start_time = datetime.now()
                top_10_tweets = get_top_10_users()
                end_time = datetime.now()
                time = (end_time - start_time).total_seconds()
                
                count = len(top_10_tweets)
                
                  
            return render_template('top.html', option=option, top_10_tweets=top_10_tweets, count=count, time=time)
            
        else:
            result = "Please select one option"
            
    return render_template('select.html', option=option, result=result)



def query_records_by_username(textkeyword):
    key = "u_{}".format(textkeyword)
    try:
        cached_response = cache.get(key)
        if cached_response:
            cb_result = cached_response[0][0]
            pg_data = cached_response[0][1]
        else:
            # Fetch data from PostgreSQL
            pg_cursor.execute("SELECT id, name, profile_image_url_https, verified, description, url, location, screen_name, followers_count, friends_count FROM user_data1 WHERE name LIKE '{}'".format(textkeyword))
            pg_data = pg_cursor.fetchall()

            user_ids = []
            for row in pg_data:
                print("PostgreSQL Row:", row[0])
                user_ids.append(row[0])

            # Construct the N1QL query with the modified pattern
            query = f"SELECT *  FROM Twitter_Dataset.Tweet_Data.Tweets_Data WHERE user_id IN $userid and retweet_id is null order by created_at desc , retweet_count desc , reply_count desc"
            options = QueryOptions(named_parameters={"userid": user_ids})
            
            # Execute the query
            cb_result = list(cluster.query(query, options))
            cache.set(key, [cb_result, pg_data])
        # for row in cb_result:
        #             print("Couchbase Row:", row)
        
        # Process the joined data
        joined_data = []
        for pg_row in pg_data:
            for cb_row in cb_result:
                if pg_row[0] == cb_row['Tweets_Data']['user_id']:
                    joined_row = {
                        'couchbase_data': cb_row,
                        'postgresql_data': {'id': pg_row[0], 'name': pg_row[1] ,'profile_url': pg_row[2] , 'verified': pg_row[3] , 'description': pg_row[4], 'url': pg_row[5] , 'location' : pg_row[6] , 'screen_name' : pg_row[7] , 'followers_count' : pg_row[8] , 'friends_count' : pg_row[9]} 
                    }
                    joined_data.append(joined_row)
        # Print or process the joined data
            for joined_row in joined_data:
                print("Joined data:", joined_row)

        return joined_data
    
    except Exception as e:
        # return render_template("index.html")
        # return flask.send_file("index.html")
        print("An error occurred:", e)
        return None



def query_records_by_text(textkeyword):
    try:
        print("cache keys: ", cache.cache.keys())
        key = "t_{}".format(str.lower(textkeyword))
        # print(key)
        cached_response = cache.get(key)
        # if key in cache.cache.keys():
        #     cb_result = cache.cache[key][0]
        #     pg_data = cache.cache[key][1]
        # print(cached_response[0][0])
        if cached_response:
            cb_result = cached_response[0][0]
            pg_data = cached_response[0][1]
            
        else:
            print("Not cached")
            # Check if the pattern already contains the wildcard '%'
            if "%" not in textkeyword:
                textkeyword = f"%{textkeyword}%"

            # Construct the N1QL query with the modified pattern
            query = f"SELECT *  FROM Twitter_Dataset.Tweet_Data.Tweets_Data WHERE text LIKE $textkeyword and retweet_id is null order by created_at desc , retweet_count desc , reply_count desc"
            options = QueryOptions(named_parameters={"textkeyword": textkeyword})
            
            # Execute the query
            cb_result = list(cluster.query(query, options))
            
            # Extract user_ids from Couchbase data
            user_ids = [row['Tweets_Data']['user_id'] for row in cb_result if 'Tweets_Data' in row and 'user_id' in row['Tweets_Data']]
            # Fetch data from PostgreSQL
            pg_cursor.execute("SELECT id, name, profile_image_url_https, verified, description, url, location, screen_name, followers_count, friends_count FROM user_data1 WHERE id IN %s", (tuple(user_ids),))
            pg_data = pg_cursor.fetchall()
            cache.set(key, [cb_result, pg_data])
            # cache.cache[key] = []
            # cache.cache[key].append(cb_result)
            # cache.cache[key].append(pg_data)
        

        # Process the joined data
        joined_data = []
        for cb_row in cb_result:
            for pg_row in pg_data:
                if cb_row['Tweets_Data']['user_id'] == pg_row[0]: 
                    joined_row = {
                        'couchbase_data': cb_row,
                        'postgresql_data': {'name': pg_row[1] ,'profile_url': pg_row[2] , 'verified': pg_row[3] , 'description': pg_row[4], 'url': pg_row[5] , 'location' : pg_row[6] , 'screen_name' : pg_row[7] , 'followers_count' : pg_row[8] , 'friends_count' : pg_row[9]} 
                    }
                    joined_data.append(joined_row)

        return joined_data
    
    except Exception as e:
        print("An error occurred:", e)
        return None

def query_records_by_textanddate(textkeyword, from_date, to_date):
    try:
        # Check if the pattern already contains the wildcard '%'
        if "%" not in textkeyword:
            textkeyword = f"%{textkeyword}%"

        # Construct the N1QL query with the modified pattern
        query = f"SELECT * FROM `Twitter_Dataset`.Tweet_Data.Tweets_Data WHERE date between $from_date and $to_date and text like $textkeyword and retweet_id is null order by created_at desc, retweet_count desc, reply_count desc"
        options = QueryOptions(named_parameters={"from_date": from_date , "to_date": to_date , "textkeyword": textkeyword})
        
        # Execute the query
        cb_result = list(cluster.query(query, options))
        
        # Extract user_ids from Couchbase data
        user_ids = [row['Tweets_Data']['user_id'] for row in cb_result if 'Tweets_Data' in row and 'user_id' in row['Tweets_Data']]
        
        # Fetch data from PostgreSQL
        pg_cursor.execute("SELECT id, name, profile_image_url_https, verified, description, url, location, screen_name, followers_count, friends_count FROM user_data1 WHERE id IN %s", (tuple(user_ids),))
        pg_data = pg_cursor.fetchall()
        
        # Process the joined data
        joined_data = []
        for cb_row in cb_result:
            for pg_row in pg_data:
                if cb_row['Tweets_Data']['user_id'] == pg_row[0]: 
                    joined_row = {
                        'couchbase_data': cb_row,
                        'postgresql_data': {'name': pg_row[1] ,'profile_url': pg_row[2] , 'verified': pg_row[3] , 'description': pg_row[4], 'url': pg_row[5] , 'location' : pg_row[6] , 'screen_name' : pg_row[7] , 'followers_count' : pg_row[8] , 'friends_count' : pg_row[9]} 
                    }
                    joined_data.append(joined_row)

        return joined_data
    
    except Exception as e:
        print("An error occurred:", e)
        return None


def query_records_by_hashtagandsource(hashtag, source):
    key = "h_{}_{}".format(hashtag, source)
    try:
        cached_response = cache.get(key)
        if cached_response:
            cb_result = cached_response[0][0]
            pg_data = cached_response[0][1]
        else:

            # Check if the pattern already contains the wildcard '%'
            if "%" not in hashtag:
                hashtag = f"%{hashtag}%"
            if "%" not in source:
                source = f"%{source}%"

            # Construct the N1QL query with the modified pattern
            # query = f"SELECT * FROM Twitter_Dataset.Tweet_Data.Tweets_Data WHERE ANY hashtag IN hashtag_list SATISFIES hashtag LIKE $hashtag END and source like $source and  retweet_id is null order by created_at desc, retweet_count desc, reply_count desc"
            query = f"SELECT * FROM Twitter_Dataset.Tweet_Data.Tweets_Data WHERE ANY hashtag IN hashtag_list SATISFIES hashtag LIKE $hashtag END and source like $source order by created_at desc, retweet_count desc, reply_count desc"

            options = QueryOptions(named_parameters={"hashtag": hashtag , "source": source })
            
            # Execute the query
            cb_result = list(cluster.query(query, options))
            
            # Extract user_ids from Couchbase data
            user_ids = [row['Tweets_Data']['user_id'] for row in cb_result if 'Tweets_Data' in row and 'user_id' in row['Tweets_Data']]
            
            # Fetch data from PostgreSQL
            pg_cursor.execute("SELECT id, name, profile_image_url_https, verified, description, url, location, screen_name, followers_count, friends_count FROM user_data1 WHERE id IN %s", (tuple(user_ids),))
            pg_data = pg_cursor.fetchall()
            cache.set(key, [cb_result, pg_data])

        # Process the joined data
        joined_data = []
        for cb_row in cb_result:
            for pg_row in pg_data:
                if cb_row['Tweets_Data']['user_id'] == pg_row[0]: 
                    joined_row = {
                        'couchbase_data': cb_row,
                        'postgresql_data': {'name': pg_row[1] ,'profile_url': pg_row[2] , 'verified': pg_row[3] , 'description': pg_row[4], 'url': pg_row[5] , 'location' : pg_row[6] , 'screen_name' : pg_row[7] , 'followers_count' : pg_row[8] , 'friends_count' : pg_row[9]} 
                    }
                    joined_data.append(joined_row)

        return joined_data
    
    except Exception as e:
        print("An error occurred:", e)
        return render_template()

def query_records_by_language(textkeyword, language):
    key = "l_{}_{}".format(textkeyword, language)
    try: 
        cached_response = cache.get(key)
        if cached_response:
            cb_result = cached_response[0][0]
            pg_data = cached_response[0][1]
        else:
            # Check if the pattern already contains the wildcard '%'
            if "%" not in textkeyword:
                textkeyword = f"%{textkeyword}%"
                
            # Construct the N1QL query with the modified pattern
            query = f"SELECT * FROM Twitter_Dataset.Tweet_Data.Tweets_Data WHERE text like $textkeyword and lang = $language and retweet_id is null order by created_at desc, retweet_count desc, reply_count desc"
            options = QueryOptions(named_parameters={"textkeyword": textkeyword, "language": language}) 

            # Execute the query
            cb_result = list(cluster.query(query, options))

            # Extract user_ids from Couchbase data
            user_ids = [row['Tweets_Data']['user_id'] for row in cb_result if 'Tweets_Data' in row and 'user_id' in row['Tweets_Data']]
            
            # Fetch data from PostgreSQL
            pg_cursor.execute("SELECT id, name, profile_image_url_https, verified, description, url, location, screen_name, followers_count, friends_count FROM user_data1 WHERE id IN %s", (tuple(user_ids),))
            pg_data = pg_cursor.fetchall()
            cache.set(key, [cb_result, pg_data])

        # Process the joined data
        joined_data = []
        for cb_row in cb_result:
            for pg_row in pg_data:
                if cb_row['Tweets_Data']['user_id'] == pg_row[0]: 
                    joined_row = {
                        'couchbase_data': cb_row,
                        'postgresql_data': {'name': pg_row[1] ,'profile_url': pg_row[2] , 'verified': pg_row[3] , 'description': pg_row[4], 'url': pg_row[5] , 'location' : pg_row[6] , 'screen_name' : pg_row[7] , 'followers_count' : pg_row[8] , 'friends_count' : pg_row[9]} 
                    }
                    joined_data.append(joined_row)
            
        return joined_data
    
    except Exception as e:
        print("An error occurred:", e)
        return None


def get_top_10_users():
    try:
        query = f"select user_id , count(*) as tweet_count from Twitter_Dataset.Tweet_Data.Tweets_Data where retweet_id is null group by user_id order by tweet_count desc limit 10"
        
        # Execute the query
        cb_result = list(cluster.query(query))
        
        # Extract user_ids from Couchbase data
        user_ids = [row['user_id'] for row in cb_result if 'user_id' in row]
        print("Couchbase user_ids:", user_ids)
        
        # Fetch data from PostgreSQL
        pg_cursor.execute("SELECT id, name, profile_image_url_https, verified, description, url, location, screen_name, followers_count, friends_count FROM user_data1 WHERE id IN %s", (tuple(user_ids),))
        pg_data = pg_cursor.fetchall()
        
        # Process the joined data
        joined_data = []
        for cb_row in cb_result:
            for pg_row in pg_data:
                if cb_row['user_id'] == pg_row[0]: 
                    joined_row = {
                        'couchbase_data': cb_row,
                        'postgresql_data': {'name': pg_row[1] ,'profile_url': pg_row[2] , 'verified': pg_row[3] , 'description': pg_row[4], 'url': pg_row[5] , 'location' : pg_row[6] , 'screen_name' : pg_row[7] , 'followers_count' : pg_row[8] , 'friends_count' : pg_row[9]} 
                    }
                    joined_data.append(joined_row)

        return joined_data
    
    except Exception as e:
        print("An error occurred:", e)
        return None

def get_top_10_tweets():
    try:
        # Fetch data from Couchbase and store in a list
        cb_result = list(cluster.query("SELECT * FROM `Twitter_Dataset`.Tweet_Data.Tweets_Data order by retweet_count desc LIMIT 10"))
            
        # Extract user_ids from Couchbase data
        user_ids = [row['Tweets_Data']['user_id'] for row in cb_result if 'Tweets_Data' in row and 'user_id' in row['Tweets_Data']]

        # Fetch data from PostgreSQL
        pg_cursor.execute("SELECT id, name, profile_image_url_https, verified, description, url, location, screen_name, followers_count, friends_count FROM user_data1 WHERE id IN %s", (tuple(user_ids),))
        pg_data = pg_cursor.fetchall()

        # Process the joined data
        joined_data = []
        for cb_row in cb_result:
            for pg_row in pg_data:
                if cb_row['Tweets_Data']['user_id'] == pg_row[0]: 
                    joined_row = {
                        'couchbase_data': cb_row,
                        'postgresql_data': {'name': pg_row[1] ,'profile_url': pg_row[2] , 'verified': pg_row[3] , 'description': pg_row[4], 'url': pg_row[5] , 'location' : pg_row[6] , 'screen_name' : pg_row[7] , 'followers_count' : pg_row[8] , 'friends_count' : pg_row[9]} 
                        
                    }
                    joined_data.append(joined_row)

        return joined_data
    
    except Exception as e:
        print("An error occurred:", e)
        return None


@app.route("/results", methods=['GET', 'POST'])
def get_tweets():
    if request.method == 'POST':
        if option == "username":
            search_text = request.form['text']
            
            start_time = datetime.now()
            tweets = query_records_by_username(search_text)
            end_time = datetime.now()
            time = (end_time - start_time).total_seconds()
            
            count = len(tweets)
            
            return render_template('results.html', tweets=tweets, search_text=search_text, option=option, count=count, time=time)
        
        elif option == "text":
            search_text = request.form['text']
            
            start_time = datetime.now()
            tweets = query_records_by_text(search_text)
            end_time = datetime.now()
            time = (end_time - start_time).total_seconds()
            
            count = len(tweets)
            
            return render_template('results.html', tweets=tweets, search_text=search_text, option=option, count=count, time=time)
        
        elif option == "date":
            search_text = request.form['text']
            start_date = request.form["start-date"]
            end_date = request.form["end-date"]
            
            start_time = datetime.now()
            tweets = query_records_by_textanddate(search_text, start_date, end_date)
            end_time = datetime.now()
            time = (end_time - start_time).total_seconds()
            
            if type(tweets) != None:
                count = len(tweets)
            else:
                count = 0
            
            return render_template('results.html', option=option, search_text=search_text, tweets=tweets, start_date=start_date, end_date=end_date, count=count, time=time)
            
        elif option == "hashtags":
            search_text = request.form['text']
            search_source = request.form['search-source']
            start_time = datetime.now()
            tweets = query_records_by_hashtagandsource(search_text, search_source)
            end_time = datetime.now()
            time = (end_time - start_time).total_seconds()
            
            count = len(tweets)
            
            return render_template('results.html', option=option, tweets=tweets, search_text=search_text, search_source=search_source, count=count, time=time)
        
        elif option == "lang":
            search_text = request.form['text']
            search_lang = request.form['lang']
            
            start_time = datetime.now()
            tweets = query_records_by_language(search_text, search_lang)
            end_time = datetime.now()
            time = (end_time - start_time).total_seconds()
            
            count = len(tweets)
            
            return render_template('results.html', option=option, tweets=tweets, search_text=search_text, count=count, time=time, search_lang=search_lang)


 
@app.route('/user/<id>')
def info(id):
    pg_cursor.execute("SELECT id, name, profile_image_url_https, verified, description, url, location, screen_name, followers_count, friends_count FROM user_data1 WHERE id = {}".format(id))
    data = pg_cursor.fetchall()
    
    query = f"SELECT * FROM Twitter_Dataset.Tweet_Data.Tweets_Data WHERE user_id = $id order by created_at desc, retweet_count desc, reply_count desc"
    options = QueryOptions(named_parameters={"id": data[0][0]}) 

    # Execute the query
    cb_result = list(cluster.query(query, options))
    
    return render_template('user.html', data=data, cb_result=cb_result)



if __name__ == '__main__':
    app.debug = True
    app.run()