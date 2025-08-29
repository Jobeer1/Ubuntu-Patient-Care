#!/bin/bash

rm *.dcm

for i in `seq 1 3` 
do
  dump2dcm +Ug --write-xfer-little Image$i.dump Image$i.dcm
done

dump2dcm +Ug --write-xfer-little Issue131-a.dump Issue131-a.dcm
dump2dcm +Ug --write-xfer-little Issue131-b.dump Issue131-b.dcm
