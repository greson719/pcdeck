@echo off
title PCDeck Server
echo Starting PCDeck PC Server...
if exist "PCDeck.exe" (
    start "" "PCDeck.exe"
) else (
    python server\gui.py
)

