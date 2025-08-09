FROM python:3.8

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# install build tools and ImageMagick dependencies
RUN apt-get update && \
    apt-get install -y wget autoconf pkg-config build-essential nano \
    curl libpng-dev libjpeg-dev libtiff-dev libxml2-dev fontconfig libfreetype6-dev ghostscript graphviz libtool && \
    wget https://imagemagick.org/archive/ImageMagick.tar.gz && \
    mkdir /tmp/imagemagick && \
    tar -xzf ImageMagick.tar.gz --strip-components=1 -C /tmp/imagemagick && \
    rm ImageMagick.tar.gz && \
    apt-get clean && \
    apt-get autoremove -y

RUN cd /tmp/imagemagick && sh ./configure --prefix=/usr/local --with-bzlib=yes --with-fontconfig=yes --with-freetype=yes --with-gslib=yes --with-gvc=yes --with-jpeg=yes --with-jp2=yes --with-png=yes --with-tiff=yes --with-xml=yes --with-gs-font-dir=yes && \
    make -j && make install && ldconfig /usr/local/lib/ && \
    rm -rf /tmp/imagemagick

RUN git clone https://github.com/bj4rnee/DeformBot.git /deformbot

WORKDIR /deformbot

RUN pip install --no-cache-dir --upgrade -r ./requirements.txt

# finally set workdir to script location
WORKDIR /deformbot/discord