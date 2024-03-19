import os
import pickle
import pandas as pd
import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
port = 7020

def get_new_credentials():
    print("Requesting YouTube account credentials...")
    
    flow = InstalledAppFlow.from_client_secrets_file('data/tokens/client_secrets.json', scopes=['https://www.googleapis.com/auth/youtube.readonly'])  
    try: 
        flow.run_local_server(port=port, prompt='consent', authorization_prompt_message='')
    except Exception as e: 
        print(e)
        exit()
    credentials = flow.credentials
    
    username = get_account_name(credentials)    
    dir = 'data/tokens/{0}'.format(username)
    token_path = '{0}/login_info.pickle'.format(dir)

    if os.path.exists(dir):
        print("\nError: An account with the same name ({0}) has been archived before.".format(username))
        print("Would you like to overwrite the token? (Y/N)")
        while True:
            user_input = input("> ")
            if user_input == 'Y':
                break
            elif user_input == 'N':
                exit()
            else: print("Invalid option.")            
    else:
        os.makedirs(dir)

    with open(token_path, 'wb') as f:
        pickle.dump(credentials, f)
    
    return credentials, username

def get_existing_credentials(username):
    dir = 'data/tokens/{0}'.format(username)
    token_path = '{0}/login_info.pickle'.format(dir)

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            credentials = pickle.load(token)
            
            if credentials.valid:
                return credentials

            if credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                    return credentials
                except Exception as e:
                    print("Unable to refresh credentials:", e)

    print("Requesting a new token for {0}'s YouTube account...".format(username))
    
    flow = InstalledAppFlow.from_client_secrets_file('data/tokens/client_secrets.json', scopes=['https://www.googleapis.com/auth/youtube.readonly'])  
    try: 
        flow.run_local_server(port=port, prompt='consent', authorization_prompt_message='')
    except Exception as e: 
        print(e)
        exit()

    credentials = flow.credentials
    account_name = get_account_name(credentials)
    if account_name != username:
        print('Error: Credentials given [{1}] does not match with the username [{0}]'.format(username, account_name))
        exit()

    with open(token_path, 'wb') as f:
        pickle.dump(credentials, f)

    return credentials, username

def get_account_name(credentials):
    youtube = build('youtube', 'v3', credentials=credentials)

    response = youtube.channels().list(
        part='snippet',
        mine=True
    ).execute()

    account_name = response['items'][0]['snippet']['title']
    return account_name

def fetch_playlist_info(youtube):
    playlists = []
    nextPageToken = None

    while True:
        response = youtube.playlists().list(
            part="snippet,contentDetails", 
            mine=True, 
            maxResults=50,
            pageToken=nextPageToken
        ).execute()
        
        for playlist in response["items"]:
            playlists.append({
                'user': playlist['snippet']['channelTitle'],
                'p_title': playlist['snippet']['title'],
                'p_id': playlist["id"],
                'p_video_count': playlist["contentDetails"]["itemCount"],
            })
        
        nextPageToken = response.get('nextPageToken')
        if not nextPageToken:
            break

    return playlists

def fetch_playlist_videos(youtube, playlist_id):
    playlist_videos = []
    nextPageToken = None
    while True:
        response = youtube.playlistItems().list(
            part="snippet,contentDetails,status",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=nextPageToken
        ).execute()

        playlist_videos.extend(response['items'])
        nextPageToken = response.get('nextPageToken')
        
        if not nextPageToken:
            break

    return playlist_videos

def parse_video_info(video, playlist, username):
    video_info = {
        'user': playlist['user'],
        'p_title': playlist['p_title'],
        'p_id': playlist['p_id'],
        'p_video_count': playlist['p_video_count'],

        'p_index': video["snippet"]["position"],
        'p_date_added': video["snippet"]["publishedAt"],
        'v_title': video["snippet"]["title"],
        'v_id': video["snippet"]["resourceId"]["videoId"], 
        'v_status': video["status"]["privacyStatus"],
        'v_uploader': '',
        'v_uploader_id': '',
        'v_date_published': '',
        'v_description': video["snippet"]["description"],
    }
    if video_info['v_status'] not in {'private', 'privacyStatusUnspecified'}:
        video_info['v_uploader'] = video["snippet"]["videoOwnerChannelTitle"]
        video_info['v_uploader_id'] = video["snippet"]["videoOwnerChannelId"]
        video_info['v_date_published'] = video["contentDetails"]["videoPublishedAt"]

    if video_info['v_status'] not in {'unlisted', 'private', 'public', 'privacyStatusUnspecified'}:
        print("Warning: New privacyStatus detected:", video_info['v_status'])

    if video_info['user'] != username:
        print("Error: Playlist Username {0} does not match account {1}".format(video_info[0], username))

    return video_info

def get_playlist_info(username=None):
    if username is None:
        credentials, username = get_new_credentials()
    else:
        credentials = get_existing_credentials(username)    

    print("\nRequesting {0}'s Playlist Info...".format(username))        
    youtube = build('youtube', 'v3', credentials=credentials)
    playlists = fetch_playlist_info(youtube)

    videos = []
    for playlist in playlists:
        print(' ... Fetching Playlist: {}'.format(playlist['p_title']))
        playlist_videos = fetch_playlist_videos(youtube, playlist['p_id'])
        for video in playlist_videos:
            video_info = parse_video_info(video, playlist, username)
            videos.append(video_info)

    # Get liked videos playlist
    print(' ... Fetching {0}\'s Liked Playlist'.format(username))
    request = youtube.videos().list(
        part="snippet,status",
        myRating="like",
        maxResults=50
    )

    while request is not None:
        response = request.execute()
        for video in response['items']:
            video_info = {
                'user': username,
                'p_title': "Liked videos" ,
                'p_id': username + '_liked' ,
                'p_video_count': '',
                'p_index': '',
                'p_date_added': '',
                'v_title': video["snippet"]["title"],
                'v_id': video['id'],
                'v_status': video["status"]["privacyStatus"],
                'v_uploader': video["snippet"]["channelTitle"],
                'v_uploader_id': video["snippet"]["channelId"],
                'v_date_published': video["snippet"]["publishedAt"],
                'v_description': video["snippet"]["description"],
            }
            videos.append(video_info)
        request = youtube.videos().list_next(request, response)

    youtube.close()
    return videos

def read_csv(path, columns):
    if not os.path.isfile(path):
        csv = pd.DataFrame([], columns=columns)
        csv.to_csv(path, index=False)
    else:
        csv = pd.read_csv(path, encoding_errors='replace')
    return csv

def check_for_changes_since_last_archive(prev_index, curr_index):
    # find all accounts from curr_index that exist in prev_index 
    accounts = curr_index['user'].unique()

    # compare to see if there have been any changes since the last archive
    prev_index_accounts = prev_index[prev_index['user'].isin(accounts)].reset_index(drop=True).fillna('')
    curr_index = curr_index.fillna('')
    if prev_index_accounts[['p_id','v_id','v_status']].equals(curr_index[['p_id','v_id','v_status']]):
        print("\nPlaylists are identical to last check. Archiving will be skipped.")
        exit()
    return accounts

def compare_bookmarks(playlist_info):
    deleted_list = []
    privated_list = []
    recovered_list = []
    unlisted_list = []
    removed_liked_video = []
    removed_untracked_video = []

    columns = list(playlist_info[0].keys())

    curr_index = pd.DataFrame(playlist_info)        

    if not os.path.isfile('data/prev_index.csv'):
        print("\nNo previous archive detected. Creating first index...")
    prev_index = read_csv('data/prev_index.csv', columns)

    accounts = check_for_changes_since_last_archive(prev_index, curr_index)

    # 1. track privated videos
    check = curr_index[curr_index['v_status'] == 'private']
    for index, row in check.iterrows():
        match = prev_index[(prev_index['p_id'] == row['p_id']) & (prev_index['v_id'] == row['v_id'])]    
        # untracked -> private
        if match.empty:
            privated_list.append(row)
            continue
        # public/unlisted -> private
        elif match['v_status'].values[0] != 'private':
            match['v_status'].values[0] = match['v_status'].values[0] + ' -> private'
            recovered_list.append(match.iloc[0])

        # preserve the video's details in from preceding indexes
        curr_index.loc[index, ['v_title', 'v_uploader', 'v_uploader_id', 'v_date_published']] = match[['v_title', 'v_uploader', 'v_uploader_id', 'v_date_published']].values[0]

    # 2. track deleted videos
    check = curr_index[curr_index['v_status'] == 'privacyStatusUnspecified']
    for index, row in check.iterrows():
        match = prev_index[(prev_index['p_id'] == row['p_id']) & (prev_index['v_id'] == row['v_id'])]    
        # untracked -> deleted
        if match.empty:
            deleted_list.append(row)
            continue
        # public/unlisted -> deleted    
        elif match['v_status'].values[0] == 'public' or match['v_status'].values[0] == 'unlisted':
            match['v_status'].values[0] = match['v_status'].values[0] + ' -> deleted'
            recovered_list.append(match.iloc[0])
        
        # preserve the video's details in successive indexes
        curr_index.loc[index, ['v_title', 'v_uploader', 'v_uploader_id', 'v_date_published']] = match[['v_title', 'v_uploader', 'v_uploader_id', 'v_date_published']].values[0]

    # 3. track unlisted videos
    check = curr_index.loc[curr_index['v_status'] == 'unlisted']
    for index, row in check.iterrows():
        match = prev_index[(prev_index['p_id'] == row['p_id']) & (prev_index['v_id'] == row['v_id'])]    
        # untracked/public -> unlisted
        if match.empty:
            unlisted_list.append(row) 
        elif match['v_status'].values[0] == 'public':
            match['v_status'].values[0] = match['v_status'].values[0] + ' -> unlisted'
            unlisted_list.append(match.iloc[0])

    # 4. track un-privated videos
    privated_csv = read_csv('data/privated_videos.csv', columns + ['date_archived'])
    for index, row in privated_csv.iterrows():
        match = curr_index[(curr_index['p_id'] == row['p_id']) & (curr_index['v_id'] == row['v_id'])]    
        if match.empty:
            # privated -> untracked
            if row['user'] in accounts:
                removed_untracked_video.append(row)
        else:
            # private -> private
            if match['v_status'].values[0] == 'private': continue
            # private -> deleted
            elif match['v_status'].values[0] == 'privacyStatusUnspecified': deleted_list.append(row)
            # private -> public/unlisted
            else:
                match['v_status'].values[0] = 'private -> ' + match['v_status'].values[0]
                recovered_list.append(match.iloc[0])

            # remove from privated_csv when they are no longer privated
            # find instances where match has the same pid and vid as in privated csv, then remove those values from privated csv        
            privated_csv = privated_csv[~privated_csv[['p_id', 'v_id']].apply(tuple, 1).isin(match[['p_id', 'v_id']].apply(tuple, 1))]
    privated_csv.to_csv('data/privated_videos.csv', index=False)

    # 5. track liked videos that disappeared
    for username in accounts:
        liked_video_missing = []
        check = prev_index[prev_index['p_id'] == username + '_liked']
        for index, row in check.iterrows():
            match = curr_index[curr_index['v_id'] == row['v_id']]   
            if match.empty:
                # liked video -> private/deleted/manually removed              
                liked_video_missing.append(row)

        # check the new status of the missing liked video
        if liked_video_missing:
            youtube = build('youtube', 'v3', credentials=get_existing_credentials(username))
            for video in liked_video_missing:
                request = youtube.videos().list(
                    part="status",
                    id=video[7]
                )
                response = request.execute()
                # liked video -> deleted
                if not response['items']:
                    video[8] = video[8] + ' -> deleted'
                    recovered_list.append(video)
                # liked video -> privated
                elif response["items"][0]["status"]["privacyStatus"] != video[8]:
                    video[8] = video[8] + ' -> ' + response["items"][0]["status"]["privacyStatus"]
                    recovered_list.append(video)
                # liked video -> manually removed
                else:
                    removed_liked_video.append(video)
            youtube.close()

    # Print results and save them to their respective csv files.
    date = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if recovered_list or unlisted_list or deleted_list or privated_list or removed_liked_video or removed_untracked_video:
        print("\nThe Following Changes were Detected:")

        if recovered_list:
            save_index(recovered_list,'Recovered (found)', 'data/recovered_videos.csv', columns, date)
        if deleted_list:
            save_index(deleted_list,'Deleted (lost)', 'data/deleted_videos.csv', columns, date)
        if privated_list:
            save_index(privated_list,'Privated (untracked)', 'data/privated_videos.csv', columns, date)
        if unlisted_list:
            save_index(unlisted_list,'Unlisted (other)', 'data/unlisted_videos.csv', columns, date)
        
        if removed_liked_video:
            print_index(removed_liked_video, "Manually removed liked videos (other):")

        if removed_untracked_video:
            print_index(removed_untracked_video, "Notice: The following unrecovered videos were removed from your playlists:")
            
            print("Would you like to remove these entries from the archive?")
            while True:
                user_input = input("> ")
                if user_input == 'Y':
                    df1 = pd.DataFrame(removed_untracked_video, columns = columns + ['date_archived'])
                    df2 = read_csv('data/privated_videos.csv', columns + ['date_archived'])

                    merged_df = pd.merge(df2, df1[['p_id', 'v_id']], on=['p_id', 'v_id'], how='left', indicator=True)
                    df2_unique = merged_df[merged_df['_merge'] == 'left_only'].drop(columns=['_merge'])

                    df2_unique.to_csv('data/privated_videos.csv', index=False)            
                    break
                elif user_input == 'N': break
                else: print("Invalid option.")    

    else:
        print("\nPlaylists have been modified since the last check and will be saved. No status changes were detected")

    # update username entries from prev_index with curr_index
    curr_index = pd.concat([prev_index[~prev_index['user'].isin(accounts)], curr_index])
    curr_index.to_csv('data/prev_index.csv', index=False)

def print_index(list, message):
    print("{0} videos:".format(message))
    for i, f in enumerate(list):
        print(i+1,'[{1}] www.youtube.com/watch?v={2} | Title: {3}{4} | {5} | {0}'.format(f[0], f[8], f[7], f[6][:50], '...' if len(f[6]) > 49 else '', f[1]))
    print()

def save_index(list, message, path, columns, date):
    print_index(list, message)

    # save new values that do not already exist in these folders and add the date archived
    df1 = pd.DataFrame(list, columns=columns)
    df2 = read_csv(path, columns + ['date_archived'])
    df_new = df1[~df1[['p_id', 'v_id']].apply(tuple, axis=1).isin(df2[['p_id', 'v_id']].apply(tuple, axis=1))]
    df_new['date_archived'] = date
    df_new.to_csv(path, mode='a', index=False, header=False)

def select_command(prompt, options):
    print('\n'+prompt)
    for index, option in enumerate(options):
        print("{0}. {1}".format(index+1, option))

    while True:
        user_input = input('> ')
        if user_input.isnumeric() and int(user_input) > 0 and int(user_input) <= len(options):
            return options[int(user_input)-1]
        else:
            print("Invalid input. Please try again.")

if __name__ == "__main__":
    if not os.path.exists('data/tokens/client_secrets.json'):        
        print("Error: Missing Credentials in /data/tokens: OAuth Client ID Json is missing. See: (https://support.google.com/cloud/answer/6158849)")
        exit()

    accounts = []
    for file in os.scandir('data/tokens/'):
        if file.is_dir():
            accounts.append(file.name)
            continue
    
    if accounts:
        print('Current Accounts Tracked:', ', '.join(accounts))
        option = select_command('Select an Option:',['Archive all accounts', 'Archive one account', 'Add a new account'])
    else: option = 'Add a new account'

    if option == 'Archive all accounts':
        playlist_info = []
        for username in accounts:
            playlist_info += get_playlist_info(username)

    elif option == 'Archive one account':
        username = select_command('Select an Account:',accounts)
        playlist_info = get_playlist_info(username)

    elif option == 'Add a new account':
        playlist_info = get_playlist_info()
        while True:
            print("\nWould you like to add another account? (Y/N)")
            user_input = input("> ")
            if user_input == 'Y': 
                playlist_info += get_playlist_info()
            elif user_input == 'N': break
            else: print("Invalid option.")    

    compare_bookmarks(playlist_info)
