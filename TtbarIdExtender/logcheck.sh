ls -la crab/submit_2018*.log
grep -l "skip.*already exists" crab/submit_2018*.log && \
  grep -h "skip.*already exists" crab/submit_2018*.log | sed 's/.*crab_//'
