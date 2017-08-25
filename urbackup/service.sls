# -*- coding: utf-8 -*-
# vim: ft=sls

{% from "urbackup/map.jinja" import urbackup with context %}

include:
  - urbackup.install

urbackup-service:
  service.running:
    - name: {{ urbackup.service }}
    - enable: True
    - onlyif: dpkg-query -W {{ urbackup.pkg }}
