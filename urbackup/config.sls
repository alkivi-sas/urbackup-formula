# -*- coding: utf-8 -*-
# vim: ft=sls

{% from "urbackup/map.jinja" import urbackup with context %}

include:
  - urbackup.install
  - urbackup.service

urbackup-defaults:
  file.managed:
    - name: {{ urbackup.defaults }}
    - source: salt://urbackup/templates/urbackupsrv.jinja
    - template: jinja
    - mode: 755
    - user: root
    - group: root
    - watch_in:
      - service: urbackup-service

urbackup-config:
  file.managed:
    - name: {{ urbackup.config_backuppath }}
    - source: salt://urbackup/templates/backupfolder.jinja
    - template: jinja
    - mode: 644
    - user: root
    - group: root
    - watch_in:
      - service: urbackup-service

urlbackup-backuppath:
  file.directory:
    - name: {{ urbackup.config.backuppath }}
    - user: {{ urbackup.config.user }}
    - group: {{ urbackup.config.group }}
    - mode: 755
    - watch_in:
      - service: urbackup-service
