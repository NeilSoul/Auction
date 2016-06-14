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
sudo apt-get install vlc
sudo pip install python-vlc
# PyQt on MacOS
brew install pyqt
```

Plot Module (optional if need master running)
```bash
sudo pip install matplotlib
```


## Run

Usage of app.py :
```
usage: app.py [-h] [-p PEER] [-r ROLE] [-a] [-s SCENE] [-l LOG] [-v]

App

optional arguments:
  -h, --help            show this help message and exit
  -p PEER, --peer PEER  peer name
  -r ROLE, --role ROLE  role of the app, to be m(Master) or s(Slave)
  -a, --auto            if is a automatic slave
  -s SCENE, --scene SCENE
                        select a scene
  -l LOG, --log LOG     log file
  -v, --video           will play video
```

Example to run a slave
```bash
# do not show video
python app.py -r s
# set peername and show video
python app.py -p A -r s -v
# ctr + C or type 'exit' to stop a slave
```

Example to run a master (optional, simluate some scene or collect datas and plot some charts)
```bash
# simple master
python app.py -r m
```

Example to run some scene
```bash
# At one pc
python app.py -r m -s [scene code]
# At others
python app.py -r s -p [peername] -a
```



