# Metadata Retrieval & Recovery Tool
### Missing Videos
When a video in a playlist on YouTube is deleted or set to private, all information other than its URL is lost. If the video was in your default Liked Playlist, not even the URL will remain.

<img src="demo/example.png" width="600">

### The API Tool
This is a tool I developed to recover videos under these scenarios. Using YouTube's API, a snapshot of all your playlists' details are taken from your YouTube account. Then, a comparison is made with a previous snapshot to:
- find videos that were not previously unlisted/privated/deleted
- recover untracked privated videos that have been set to public again
- ignore videos that were manually removed by the user and update the previous snapshot with any new changes

It supports tracking across multiple accounts and additional accounts can be added at any time.

All information is stored locally and can always be revisited for further information. 

<img src="demo/demo.gif" width="600">
