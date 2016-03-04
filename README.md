# Auction

## Requirements

running platform : `python2.7`
software needed if play streaming : `mplayer`
python module needed : `m3u8`

```
sudo apt-get install mplayer
sudo pip install m3u8
```

energy module:
```
apt-get install python-smbus
sudo vi /boot/config.txt
```
```
# Uncomment some or all of these to enable the optional hardware interfaces
dtparam=i2c_arm=on
dtparam=i2s=on
#dtparam=spi=on
```

## Run

Usage of auctioneer :
```
usage: auctioneer.py [-h] [-p PEER] [-s SEGMENT]
optional arguments:
  -h, --help            show this help message and exit
  -p PEER, --peer PEER  name of peer
  -s SEGMENT, --segment SEGMENT
                        segments per auction
```
To stop auctioneer : 
```
Ctrl+C or input [exit]
```

Usage of bidder : 
```
usage: bidder.py [-p PEER] [-u URL] [-s]
optional arguments:
  -h, --help            show this help message and exit
  -p PEER, --peer PEER  name of peer
  -u URL, --url URL     url to play
  -s, --silent          not play video actually
```
To stop auctioneer : 
```
Ctrl+C or input [exit]
```

Run of log :
```
usage: log.py logfile
positional arguments:
  logfile     file name of the log.
```
Exit of log :
```
Ctrl+C
```

Example :

```
python log.py
# firstly open log at one terminal.
```
```
python auctioneer.py -p A -s 5
# secondly open auctioneer named A ,and set number of segment to be 5.
```

```
python bidder.py -p B -s
# thirdly open bidder name B, which  not actually play but just download.
```


