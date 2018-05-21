#!/usr/bin/python
from sys import argv, exit

from math import exp
import re

from tempfile import NamedTemporaryFile
from os import system, remove, path
from subprocess import Popen, PIPE

try:
    from string import maketrans
    t = maketrans("ATGCRYSWKMBDHV", "TACGYRWSMKVHDB")
except:
    t = str.maketrans("ATGCRYSWKMBDHV", "TACGYRWSMKVHDB")

p1 = re.compile(r"[^ATGC-]")
p2 = re.compile(r"[GC]")

def finditer_everything(pattern, string, flags=0):
    pattern = re.compile(pattern, flags=flags)
    pos = 0
    m = pattern.search(string, pos)
    while m is not None:
        yield m
        pos = m.start() + 1
        m = pattern.search(string, pos)

def target_yield(exon_seq, n=60, crrna_len=20, pam_seq="NGG", isreversed=False, seq_rois=[]):
    if n%2 == 1:
        raise Exception
    exon_seq = str(exon_seq)
    pam_seq = str(pam_seq)
    if isreversed:
        pattern = pam_seq + crrna_len*'N'
    else:
        pattern = crrna_len*'N' + pam_seq
    pattern_rev = pattern.translate(t)[::-1]
    pattern = "(" + pattern + ")|(" + pattern.translate(t)[::-1] + ")"
    pattern = pattern.replace('N', '[AGTC]').replace('R', '[AG]').replace('W', '[AT]').replace('M', '[AC]').replace('Y', '[CT]').replace('S', '[GC]').replace('K', '[GT]').replace('B', '[CGT]').replace('D', '[AGT]').replace('H', '[ACT]').replace('V', '[ACG]')
    pattern_rev = pattern_rev.replace('N', '[AGTC]').replace('R', '[AG]').replace('W', '[AT]').replace('M', '[AC]').replace('Y', '[CT]').replace('S', '[GC]').replace('K', '[GT]').replace('B', '[CGT]').replace('D', '[AGT]').replace('H', '[ACT]').replace('V', '[ACG]')
    p_rev = re.compile(pattern_rev)

    if seq_rois == []:
        seq_rois = [ [0, len(exon_seq)] ]
    tot_len = 0
    for seq_roi in seq_rois:
        tot_len += seq_roi[1] - seq_roi[0]
    tot_len -= 1

    revmatch = False
    for m in finditer_everything(pattern, exon_seq):
        for i in (1, 2,):
            if m.group(i) or revmatch:
                if i == 1:
                    if isreversed:
                        cut_pos = m.start()+len(pam_seq)+21 # Currently this only valid for Cpf1
                    else:
                        cut_pos = m.start()+crrna_len-3 # Cleavage occurs just before this position
                    seq_start = int(cut_pos-n/2)
                    seq_RGEN = m.group(i)
                    direction = '+'
                    if p_rev.match(m.group(i)) is not None:
                        revmatch = True
                else:
                    if isreversed:
                        cut_pos = m.start()-20+crrna_len # Currently this only valid for Cpf1
                    else:
                        cut_pos = m.start()+len(pam_seq)+3
                    seq_start = int(cut_pos-n/2)
                    if revmatch:
                        seq_RGEN = m.group(1).translate(t)[::-1]
                        revmatch = False
                    else:
                        seq_RGEN = m.group(i).translate(t)[::-1]
                    direction = '-'

                rel_pos = 0
                for seq_roi in seq_rois:
                    if seq_roi[0] < cut_pos < seq_roi[1]:
                        rel_pos += cut_pos - seq_roi[0]
                        seq_end = seq_start + n
                        seq_long_pre, seq_long_post = '', ''

                        if seq_start < 0:
                            seq_long_pre = '-'*int(abs(seq_start))
                            seq_start = 0
                        if seq_end > len(exon_seq):
                            seq_long_post = '-'*(seq_end-len(exon_seq))
                            seq_end = len(exon_seq)

                        seq_long = seq_long_pre + exon_seq[seq_start:seq_end] + seq_long_post
                        yield (m.group(), direction, seq_RGEN, m.start(), seq_long, rel_pos/float(tot_len)*100.0)
                        break
                    else:
                        rel_pos += seq_roi[1] - seq_roi[0]

def mich_yield(mich_seq, left, length_weight):
    #if mich_seq[0] == '-' or mich_seq[-1] == '-':
    #    yield 0, 0
    sum_score_3=0
    sum_score_not_3=0

    right=len(mich_seq)-int(left)

    dup_list = []
    for k in range(2,left)[::-1]:
        for j in range(left,left+right-k+1):
            for i in range(0,left-k+1):
                if mich_seq[i:i+k]==mich_seq[j:j+k]:
                    length=j-i
                    dup_list.append( (mich_seq[i:i+k], i, i+k, j, j+k, length) )

    for i, dup in enumerate(dup_list):
        n=0
        score_3=0
        score_not_3=0
        
        scrap=dup[0]
        left_start=dup[1]
        left_end=dup[2]
        right_start=dup[3]
        right_end=dup[4]
        length=dup[5]

        for j in range(i):
            left_start_ref=dup_list[j][1]
            left_end_ref=dup_list[j][2]
            right_start_ref=dup_list[j][3]
            right_end_ref=dup_list[j][4]

            if (left_start >= left_start_ref) and (left_end <= left_end_ref) and (right_start >= right_start_ref) and (right_end <= right_end_ref):
                if (left_start - left_start_ref)==(right_start - right_start_ref) and (left_end - left_end_ref)==(right_end - right_end_ref):
                    n+=1
            else: pass

        if n == 0:
            length_factor = round(1/exp((length)/(length_weight)),3)
            num_GC=len(re.findall('G',scrap))+len(re.findall('C',scrap))
            score=100*length_factor*((len(scrap)-num_GC)+(num_GC*2))
            if (length % 3)==0:
                flag_3 = 0
            elif (length % 3)!=0:
                flag_3 = 1

            yield ((mich_seq[0:left_end]+'-'*length+mich_seq[right_end:], scrap, str(length), 100*length_factor*((len(scrap)-num_GC)+(num_GC*2))), flag_3)

def calc_mich_score(mich_seq):
    mich_seq = mich_seq.upper().strip()

    if mich_seq[0] == '-' or mich_seq[-1] == '-':
        return [], "", ""
    tot_score = 0
    tot_not_score = 0
    tot_list = []
    for tup, flag_3 in mich_yield(mich_seq, int(len(mich_seq)/2), 20.0):
        tot_list.append(tup)
        if flag_3 == 0:
            tot_score += tup[3]
        else:
            tot_not_score += tup[3]
    mich_score = tot_score+tot_not_score
    if mich_score != 0:
        oof_score = str(tot_not_score*100.0/mich_score)
        tot_list.sort(key=lambda e: e[3], reverse=True)
        tot_list.insert(0, (mich_seq, "", 0, 0))
    else:
        oof_score = "NaN"
    return tot_list, str(mich_score), oof_score

def find_targets(query_seq, crrna_len, pam_seq, isreversed, gene_start='', seq_roi='', targetonly=False):
    seqs = []
    if query_seq[0] == '>': # FASTA
        lines = query_seq.split('\n')
        for line in lines:
            if line.strip() == '':
                continue
            if line[0] == '>':
                seqs.append( [line[1:], '', 0, []] )
            else:
                seqs[-1][1] += p1.sub('', line.upper())

        if seq_roi.strip() != '':
            for i, line in enumerate(seq_roi.strip().split('\n')):
                if i == len(seqs):
                    break
                line = line.strip()
                seqs[i][3] += [[int(j) for j in i.split('-')] for i in line.strip().split(';')]

    else:
        if '\n' in seq_roi.strip():
            raise Exception
        if seq_roi.strip() == '':
            seqs = [ ['Untitled', p1.sub('', query_seq.upper()), 0, []] ]
        else:
            line = seq_roi.strip().split('\n')[0]
            seqs = [ ['Untitled', p2.sub('', query_seq.upper()), 0, [[int(j) for j in i.split('-')] for i in line.strip().split(';')]] ]
    targets = []
    for title, seq, gene_start, seq_rois in seqs:
        if not targetonly:
            targets.append( [ title, [] ] )
        for target in target_yield(seq, 60, crrna_len, pam_seq, isreversed, seq_rois):
            if targetonly:
                if isreversed:
                    found_target = target[2][len(pam_seq):]
                else:
                    found_target = target[2][:-len(pam_seq)]
                if not found_target in targets:
                    targets.append(found_target)
            else:
                mich_list, mich_score, oof_score = calc_mich_score(target[4])
                if isreversed:
                    seedseq = target[2][len(pam_seq):]
                else:
                    seedseq = target[2][:-len(pam_seq)]
                gc = (len(p2.findall(seedseq))*100.0)/len(seedseq)
                targets[-1][1].append( [ target[2], # Found sequence
                                         target[3] + gene_start, # Position
                                         target[5], # Releative position
                                         target[1], # Direction of target
                                         gc,
                                         'N/A' if oof_score == '' else '%.1f'%float(oof_score),
                                         mich_list] )
    return targets

def print_usage():
    print("cas-designer (standalone) v1.2")
    print("")
    print("Usage: cas-designer {config_file}")
    print("")
    print("Example configuration file (last line is optional):")
    print("/path/to/organism/")
    print("/path/to/input/sequence.fa")
    print("20")
    print("NGG")
    print("NRG")
    print("5")
    print("2")
    print("2")
    print("target_region_info.txt")

def main():
    if not len(argv) == 2:
        print_usage()
        return
    with open(argv[1]) as f:
        l = f.read().strip().replace('\r', '').split("\n")

    pamseq = l[3]
    if (len(l) != 8 and len(l) != 9) or len(l[3]) != len(l[4]):
        print("Wrong input file!")
        return

    crrna_len = int(l[2])
    if crrna_len < 0:
        isreversed = True
        crrna_len = -crrna_len
    else:
        isreversed = False
 
    raw_target_dic = {}
    with open(l[1]) as f:
        if len(l) == 8:
            targets = find_targets(f.read().strip(), crrna_len, pamseq, isreversed)
        else:
            with open(l[8]) as ff:
                ll = ff.read().strip().replace('\r', '')
                targets = find_targets(f.read().strip(), crrna_len, pamseq, isreversed, '', ll)

    for entries in targets:
        for t in entries[1]:
            if isreversed:
                raw_target = t[0][len(pamseq):]
            else:
                raw_target = t[0][:-len(pamseq)]
            if not raw_target in raw_target_dic:
                raw_target_dic[raw_target] = ['', '', ''] + [0]*(int(l[5])+1)

    with NamedTemporaryFile('wt') as f:
        print("Created temporary file: " + f.name)

        f.write(l[0] + '\n')
        if isreversed:
            f.write(l[4] + crrna_len*'N' + ' ' + l[6] + ' ' + l[7] + '\n')
        else:
            f.write(crrna_len*'N' + l[4] + ' ' + l[6] + ' ' + l[7] + '\n')
        for raw_target in raw_target_dic:
            if isreversed:
                f.write(len(pamseq)*'N' + raw_target + ' ' + l[5] + '\n')
            else:
                f.write(raw_target + len(pamseq)*'N' + ' ' + l[5] + '\n')
        f.flush()

        print("Running Cas-OFFinder...")
        p = Popen( ('cas-offinder-bulge', f.name, 'G', f.name + "_out"), stdout=PIPE, stderr=PIPE )
        rtn = p.wait()
        if rtn != 0:
            print("Cas-OFFinder is unexpectedly interrupted.")
            exit(rtn)

    print("Summing up...")
    with open(f.name + "_out") as f:
        for line in f:
            if line[0] == '#':
                continue
            entries = line.split('\t')
            entries[1] = entries[1].replace('-', '')
            if isreversed:
                if entries[0] == 'X':
                    raw_target_dic[entries[1][len(pamseq):]][3 + int(entries[6])] += 1
                    raw_target_dic[entries[1][len(pamseq):]][0] += line
                elif entries[0] == 'DNA':
                    raw_target_dic[entries[1][len(pamseq):]][1] += line
                else:
                    raw_target_dic[entries[1][len(pamseq):]][2] += line 
            else:
                if entries[0] == 'X':
                    raw_target_dic[entries[1][:-len(pamseq)]][3 + int(entries[6])] += 1
                    raw_target_dic[entries[1][:-len(pamseq)]][0] += line
                elif entries[0] == 'DNA':
                    raw_target_dic[entries[1][:-len(pamseq)]][1] += line
                else:
                    raw_target_dic[entries[1][:-len(pamseq)]][2] += line
    remove(f.name)

    print("Writing to files...")
    prefix = path.splitext(path.basename(argv[1]))[0] + "-"
    fo1 = open(path.join(path.dirname(argv[1]), prefix + "summary.txt"), "w")
    fo2 = open(path.join(path.dirname(argv[1]), prefix + "mich_patterns.txt"), "w")
    fo3 = open(path.join(path.dirname(argv[1]), prefix + "offtargets.txt"), "w")
    fo4 = open(path.join(path.dirname(argv[1]), prefix + "dna_bulges.txt"), "w")
    fo5 = open(path.join(path.dirname(argv[1]), prefix + "rna_bulges.txt"), "w")

    for target in targets:
        fo1.write(target[0]+'\n')
        fo2.write(target[0]+'\n')
        fo3.write(target[0]+'\n')
        fo4.write(target[0]+'\n')
        fo5.write(target[0]+'\n')
        fo1.write('#RGEN Target (5\' to 3\')\tPosition\tRelative Position\tDirection\tGC Contents (w/o PAM)\tOut-of-frame Score')
        for mis in range(int(l[5])+1):
            fo1.write('\tMismatch %d'%mis)
        fo1.write('\n')
        for entries in target[1]:
            fo1.write('\t'.join(map(str, entries[:-1])))
            if isreversed:
                for i in raw_target_dic[entries[0][len(pamseq):]][3:]:
                    fo1.write('\t' + str(i))
            else:
                for i in raw_target_dic[entries[0][:-len(pamseq)]][3:]:
                    fo1.write('\t' + str(i))
            fo1.write('\n')

            fo2.write(entries[0] + '\n')
            if entries[-1] != []:
                for entries_entries in entries[-1]:
                    if entries_entries[-3] == "":
                        fo2.write(entries_entries[0] + "\tWild type\n")
                    else:
                        fo2.write('\t'.join(map(str, entries_entries)) + '\n')
            else:
                fo2.write('N/A\n')

            fo3.write(entries[0] + '\n')
            if isreversed:
                lines = raw_target_dic[entries[0][len(pamseq):]][0]
            else:
                lines = raw_target_dic[entries[0][:-len(pamseq)]][0]
            if lines == "":
                fo3.write("N/A\n")
            else:
                fo3.write('#Bulge type\tcrRNA\tDNA\tChromosome\tPosition\tDirection\tMismatches\tBulge Size\n')
                fo3.write(lines)
            fo4.write(entries[0] + '\n')
            if isreversed:
                lines = raw_target_dic[entries[0][len(pamseq):]][1]
            else:
                lines = raw_target_dic[entries[0][:-len(pamseq)]][1]
            if lines == "":
                fo4.write("N/A\n")
            else:
                fo4.write('#Bulge type\tcrRNA\tDNA\tChromosome\tPosition\tDirection\tMismatches\tBulge Size\n')
                fo4.write(lines)
            fo5.write(entries[0] + '\n')
            if isreversed:
                lines = raw_target_dic[entries[0][len(pamseq):]][2]
            else:
                lines = raw_target_dic[entries[0][:-len(pamseq)]][2]
            if lines == "":
                fo5.write("N/A\n")
            else:
                fo5.write('#Bulge type\tcrRNA\tDNA\tChromosome\tPosition\tDirection\tMismatches\tBulge Size\n')
                fo5.write(lines)
 
    fo1.close()
    fo2.close()
    fo3.close()
    fo4.close()
    fo5.close()

    print("Done!")
if __name__ == "__main__":
    main()
