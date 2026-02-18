# Tidal-library-data-transfer-Rewrited
A tiny tool to transfer all your music between 2 Tidal accounts. I'm rewrited my old code to work with new Tidal API by EbbLabs.


I'm Maverick565, i was lost my old Github account, because of lost phone with 2FA. Meantime there was massive changes in Tidal API since latest version of Tidal Library Data Transfer so i decided to make new repo. I made some minor changes, now there is no separated apps for albums, artists, playlists and tracks, now you could choose action in CLI by input corresponding number. You could also transfer everything like before, just choose "5" from list.

1 - Favorite Tracks

2 - Albums

3 - Artists

4 - Playlists (Cloned with custom order)

5 - Everything

When you make mistake for example, transfer something from wrong account, you could delete tracks, artists, playlists or albums, and also you could wipe everything, but use it carefully to not delete items from source account, double check you're logged to proper account from which you want to delete items.

For .exe you don't need to have installed dependencies.

## Setup:
1. Download and install latest Tidal API from EbbLabs:

```bash
python -m pip install git+https://github.com/EbbLabs/python-tidal.git
```

2. 
```bash
    pip install tqdm

```
3. Run the script as desired.

4. If you like my work and helps you, please consider donating:
https://www.paypal.com/donate/?hosted_button_id=7CUBRK3ZGKY6A
