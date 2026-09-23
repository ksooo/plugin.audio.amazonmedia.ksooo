# Amazon (Music) mediathek
Unofficial Kodi addon for Amazon Prime Music and Amazon Unlimited Music to search and play Music.
An Amazon account is necessary to use the service.

> [!IMPORTANT]
> Playback only works on Kodi for Android. On desktop platforms Amazon's licence server refuses the DRM licence
> with `VMP_VALIDATION_FAILED`, because Kodi cannot provide a Widevine Verified Media Path.
> Browsing and searching work everywhere.

## Origin
This addon is based on [Amazon (Music) mediathek](https://github.com/spacys/mediathek) by spacy, whose development was stopped. It is developed further here, independently of the original, and uses its own addon id `plugin.audio.amazonmedia.ksooo`, so both can be installed side by side.

## Installation
Install [my repository](https://ksooo.github.io/repository.kodi.ksooo/) to receive updates automatically.

## Motivation
An easy-to-use way to listen to Amazon Music through Kodi.

## Features
This addon provides an easy access to the Amazon Music world with your own Amazon account. It is possible to search for Playlists, Albums, Songs and Artists; to see the Amazon recommendations, the popular Playlists/Albums and the purchased Albums/Songs.

To play the songs it is necessary to install as well InputStream Adaptive.

## Supported Domains
Only the German domain is tested. The other domains are prepared and their Amazon sign-in pages answer, but nobody has signed in and played a track there yet. Reports are welcome.

| Country | Domain | URL | Comment |
|--|--|--|--|
| Germany | DE | https://music.amazon.de | Tested |
| France | FR | https://music.amazon.fr | Untested |
| Great Britain | UK | https://music.amazon.co.uk | Untested |
| Italy | IT | https://music.amazon.it | Untested |
| Spain | ES | https://music.amazon.es | Untested |

## Languages
The add-on is translated into German, French and Italian. The language follows Kodi's own language setting, not the domain. For any other language Kodi falls back to English. The French and Italian translations have not been reviewed by native speakers yet; corrections are welcome.
