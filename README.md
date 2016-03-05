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
usage: auctioneer.py [-h] [-p PEER] [-s SEGMENT] [-c CAPACITY] [-t TIMECOST]
                     [-l LTE] [-w WIFI] [-d DELAY] [-a BROADCAST]

Auctioneer

optional arguments:
  -h, --help            show this help message and exit
  -p PEER, --peer PEER  name of peer
  -s SEGMENT, --segment SEGMENT
                        segments per auction
  -c CAPACITY, --capacity CAPACITY
                        initial capacity
  -t TIMECOST, --timecost TIMECOST
                        rebuffer time cost coefficient
  -l LTE, --lte LTE     lte cost coefficient
  -w WIFI, --wifi WIFI  WiFi cost coefficient
  -d DELAY, --delay DELAY
                        delay of data transport.
  -a BROADCAST, --broadcast BROADCAST
                        udp broadcast address
```
To stop auctioneer : 
```
Ctrl+C or input [exit]
```

Usage of bidder : 
```
usage: bidder.py [-h] [-p PEER] [-u URL] [-s] [-t THETA] [-q QUALITY]
                 [-b BUFFER] [-m MBUFFER] [-a BROADCAST]

Bidder

optional arguments:
  -h, --help            show this help message and exit
  -p PEER, --peer PEER  name of peer
  -u URL, --url URL     url to play
  -s, --silent          not play video actually
  -t THETA, --theta THETA
                        bidder preference theta
  -q QUALITY, --quality QUALITY
                        bidder quality coefficient
  -b BUFFER, --buffer BUFFER
                        bidder buffer coefficient
  -m MBUFFER, --mbuffer MBUFFER
                        bidder max buffer
  -a BROADCAST, --broadcast BROADCAST
                        udp broadcast address
```
To stop auctioneer : 
```
Ctrl+C or input [exit]
```

Run of log :
```
usage: log.py [-h] [-l LOGFILE]

Logger

optional arguments:
  -h, --help            show this help message and exit
  -l LOGFILE, --logfile LOGFILE
                        file name of the log.
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


