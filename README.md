# Auction

## Requirements

python : `python2.7`

### Python Module Needed

M3U8 Module
```bash
sudo pip install m3u8
```

Energy Module (optional)
```bash
apt-get install python-smbus
```
edit `/boot/config.txt`
```
# Uncomment some or all of these to enable the optional hardware interfaces
dtparam=i2c_arm=on
dtparam=i2s=on
#dtparam=spi=on
```
edit `/etc/modules`, appending
```
i2c-bcm2708
i2c-ev
```

Player Module (optional if need to show video)
```bash
# vlc
# PyQt
```

Plot Module (optional if need master running)
```bash
sudo pip install matplotlib
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

Run of Script:
```
usage: script.py [-h] [-c] [-l LOGFILE] [-p PEER]

Script

optional arguments:
  -h, --help            show this help message and exit
  -c, --center          if is a role of center(peer default)
  -l LOGFILE, --logfile LOGFILE
                        file name of the log.
  -p PEER, --peer PEER  peer name
```

Example (Manual):

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

Example (Script):

at peer
```
python script.py -p A
```

at center
```
python script.py -c
```


