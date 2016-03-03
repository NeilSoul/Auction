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

auctioneer :
```
# run 
python auctioneer.py --peer [optional peer name] --segment [optional segment number per auction]
# stop
ctrl+c or exit
```
To stop auctioneer : `ctr+c` or `exit`

bidder : 
```
# run
python bidder.py --peer [optional peer name] --url [optional url] [--silent]
# stop
ctrl+c or exit
```

log:
```
# run
python log.py
```

