#!/bin/bash
# Generate a 32-byte random number and encode it in base64 format

echo "$(openssl rand -base64 32)"
