# -*- coding: utf-8 -*-
# vim: ft=sls

{% from "urbackup/map.jinja" import urbackup with context %}

urbackup_dependencies:
  pkg.installed:
    - pkgs:
      - sqlite3

urbackup_source:
  file.managed:
    - name: /tmp/urbackup-server_2.1.19_amd64.deb
    - source: https://hndl.urbackup.org/Server/2.1.19/urbackup-server_2.1.19_amd64.deb
    - source_hash: sha256=661d0e106e9abf40701b2788be8560197b3dea0902696098f6b828118b90608e
    - prereq_in:
      - cmd: urbackup_install

urbackup_install:
  debconf.set:
    - name: {{ urbackup.pkg }}
    - data: { 'urbackup/backuppath': {'type': 'string', 'value': {{ urbackup.config.backuppath}} } }
    - prereq_in:
      - cmd: urbackup_install
  cmd.run:
    - name: dpkg -i /tmp/urbackup-server_2.1.19_amd64.deb
    - unless: dpkg-query -W {{ urbackup.pkg }}
    - require:
      - pkg: urbackup_dependencies
