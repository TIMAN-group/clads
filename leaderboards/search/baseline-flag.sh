#!/bin/bash
docker-compose exec mongo \
    mongo competition --eval \
    "db.results.update( \
        {'username': '$1'}, \
        {$set: {'is_baseline': $2}}, \
        {'multi': true} \
    );"
