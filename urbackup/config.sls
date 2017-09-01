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

urbackup-backuppath:
  file.directory:
    - name: {{ urbackup.config.backuppath }}
    - user: {{ urbackup.config.user }}
    - group: {{ urbackup.config.group }}
    - mode: 750
    - watch_in:
      - service: urbackup-service
  urbackup_setting.present:
    - name: backupfolder
    - value: {{ urbackup.config.backuppath }}

{% for setting, value in urbackup.get('settings', {}).items() %}
urbackup-setting-{{ setting }}:
  urbackup_setting.present:
    - name: {{ setting }}
    - value: {{ value }}
{% endfor %}
