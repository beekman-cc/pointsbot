import praw
import prawcore
import pickle
import time

# Reddit API credentials
reddit = praw.Reddit(
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_CLIENT_SECRET',
    username='YOUR_REDDIT_USERNAME',
    password='YOUR_REDDIT_PASSWORD',
    user_agent='YOUR_USER_AGENT'
)

# Subreddit to target
subreddit = reddit.subreddit('YOUR_SUBREDDIT')

# File to store user points
points_file = 'points.pickle'

# Load the user points from file, or create a new dict if the file doesn't exist
try:
    with open(points_file, 'rb') as f:
        user_points = pickle.load(f)
except FileNotFoundError:
    user_points = {}

def save_points():
    with open(points_file, 'wb') as f:
        pickle.dump(user_points, f)

def update_flair(user, score):
    # Update the user's flair with their score
    headers = {
        'User-Agent': reddit.user_agent,
        'Authorization': 'bearer {}'.format(reddit.access_token),
    }
    data = {
        'name': user,
        'text': 'Score: {}'.format(score),
    }
    response = prawcore.Session().request(
        'PATCH',
        'https://oauth.reddit.com/r/{}/api/flair'.format(subreddit),
        headers=headers,
        json=data,
    )
    response.raise_for_status()

# Give the user points when they post or comment
def process_submission(submission):
    author = submission.author.name
    user_points[author] = user_points.get(author, 0) + 1
    save_points()
    update_flair(author, user_points[author])

    # Give points to the OP if requested
    for comment in submission.comments:
        if not isinstance(comment, praw.models.MoreComments):
            match = re.search('^!points give ([0-9]+)', comment.body)
            if match:
                giver = comment.author.name
                points_to_give = int(match.group(1))
                if user_points.get(giver, 0) >= points_to_give:
                    user_points[giver] -= points_to_give
                    save_points()
                    update_flair(giver, user_points[giver])
                    user_points[author] += points_to_give
                    save_points()
                    update_flair(author, user_points[author])
                    comment.reply(f'{points_to_give} points given to {author}')
                else:
                    comment.reply('Not enough points to give, earn some points first.')

# Monitor the subreddit for new submissions and comments
while True:
	for submission in subreddit.new(limit=10):
		if submission.created_utc > time.time() - 5:
			process_submission(submission)
			time.sleep(5)
