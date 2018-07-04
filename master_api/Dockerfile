# Ancoris master (Python 3.6)
# Copyright (C) 2018 Rodrigo Martínez <dev@brunneis.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

FROM brunneis/python:3.6.4
MAINTAINER "Rodrigo Martínez" <dev@brunneis.com>

################################################
# ANCORIS MASTER
################################################

RUN \
    pip install --upgrade pip \
    && pip install \
        pyyaml \
        consulate \
        flask \
        flask-restful \
        humanfriendly

ADD ancoris-master.tar.gz /opt/ancoris

WORKDIR /opt/ancoris
ENTRYPOINT ["python", "master.py"]
