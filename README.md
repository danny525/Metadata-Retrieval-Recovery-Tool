# Metadata Retrieval & Recovery Tool

### Missing Videos
When a video in a playlist on YouTube is deleted or set to private, all information other than its URL is lost. What's worse, is that if the video was in your default Liked Playlist, it will disappear with no trace at all.

<img src="demo/example.png" width="600">

### The API Tool

This is a tool I developed to recover videos in these scenarios. Using YouTube's API, it takes a snapshot of all the playlists on your YouTube account and saves this data locally. It will hold a record of useful information such as each video's title, uploader, video status, playlist, and description. Once it is rerun at a later date, it will compare the differences between snapshots and find and recover any lost videos.

<img src="demo/demo.gif" width="600">

