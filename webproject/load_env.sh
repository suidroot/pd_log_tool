#!/bin/bash

while IFS== read -r key value; do
  printf -v "$key" %s "$value" && export "$key"
done < ../stack.env
