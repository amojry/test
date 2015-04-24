#coding: gb18030
#!/usr/bin/env python
import sys, re, os, codecs
import math

class NBTextClassifier:
    def __init__(self):
        self.N = 0
        self.D = 0
        self.C = dict()
        self.pathinfo = dict()
        self.charset = dict()
        self.vcb = dict()
        self.high_freq = dict()
        self.entity = dict()
        self.log_C = dict()
        self.log_C2W = dict()
        self.log_base = dict()
        self.noisy_words = dict()
        self.ime_buckets = dict()
        self.C2W = dict()
        self.WDF = dict()
        self.WTF = dict()
        self.IDF = dict()
        self.LOG_BASE = math.log(0.985)
        self.fixed_class = dict()
    
    def conf( self, file_conf ):
        with open(file_conf) as conf:
            for l in conf:
                p = re.split('\s+', l.strip())
                if len(p) != 2: continue
                self.pathinfo[p[0]] = p[1]
            conf.close()
    def load_data( self ):
        with codecs.open(self.pathinfo['charset'], 'r', 'gb18030') as charset:
            for l in charset:
                p = re.split('\s+', l.strip())
                if len(p)==0: conintue
                self.charset[p[0]] = 1
            charset.close()
        with codecs.open(self.pathinfo['fixed_class'], 'r', 'gb18030') as fixed_class:
            for l in fixed_class:
                p = re.split('\s+', l.strip())
                if len(p)==0: conintue
                self.fixed_class[p[0]] = 1
            fixed_class.close()
        be_in_buckets = dict()
        with codecs.open(self.pathinfo['ime_buckets'], 'r', 'gb18030') as ime_buckets:
            for l in ime_buckets:
                p = re.split('\s+', l.strip())
                if len(p) != 3: continue
                k = p[0]+u'.'+p[1]
                self.ime_buckets[k] = 1
                be_in_buckets[p[1]] = 1
                self.entity[p[1]] = True
            ime_buckets.close()
        with codecs.open(self.pathinfo['entity'], 'r', 'gb18030') as entity:
            for l in entity:
                p = re.split( '\s+', l.strip() )
                if len(p)!=2: continue
                w = p[0]
                self.entity[w] = True
            entity.close()
        with codecs.open(self.pathinfo['high_freq'], 'r', 'gb18030') as high_freq:
            for l in high_freq:
                p = re.split('\s+', l.strip())
                if len(p)==0: conintue
                if p[0] in be_in_buckets: continue
                self.high_freq[p[0]] = 1
            high_freq.close()
        with codecs.open(self.pathinfo['noisy_words'], 'r', 'gb18030') as noisy:
            for l in noisy:
                p = re.split('\s+', l.strip())
                if len(p)==0: conintue
                if p[0] in be_in_buckets: continue
                self.noisy_words[p[0]] = 1
            noisy.close()
        self.vcb_lowbound = 0
        with codecs.open(self.pathinfo['vcb'], 'r', 'gb18030') as vcb:
            for l in vcb:
                p = re.split( '\s+', l.strip() )
                if len(p)!=2: continue
                w = p[0]
                p = float(p[1])
                self.vcb[w] = p
            vcb.close()

    def doc2sents(self, doc):
        sent_list = dict()
        sent = u''
        for c in doc:
            if not c in self.charset:
                if sent != u'':
                    if sent in sent_list: sent_list[sent] += 1
                    else: sent_list[sent] = 1
                sent = u''
            else: sent += c
        if sent != u'':
            if sent in sent_list: sent_list[sent] += 1
            else: sent_list[sent] = 1
        return sent_list
    def sent2words(self, sent, count):
        tlen = len(sent)+1
        v = list()
        p = list()
        for i in range(tlen):
            v.append(10000000000)
            p.append('')
        v[0] = 0
        p[0] = ''
        for i in range(1, tlen):
            for j in range(1,tlen):
                k = i-j
                if k < 0: continue
                tw = sent[k:i]
                tv = 0
                if not self.vcb.has_key(tw): tv = v[k] + 10000000000
                else: tv = v[k] + self.vcb[tw] 
                if v[i] > tv: 
                    v[i] = tv
                    if k == 0: p[i] = tw
                    else: p[i] = p[k] + u'/' + tw
        wordlist = dict()
        #print sent
        #print p[tlen-1].strip()
        for word in re.split(u'/', p[tlen-1].strip()):
            #if not word in self.entity: continue
            if word in wordlist: wordlist[word] += 1
            else: wordlist[word] = 1
        return wordlist
    
    def doc2words(self, doc):
        words = dict()
        for sent, count in self.doc2sents( doc ).iteritems():
            for word, occ in self.sent2words( sent, count ).iteritems():
                if word in words: words[word] += occ
                else: words[word] = occ
        return words
        	
    def train (self):
        i = 0
        with open( self.pathinfo['corpus'] ) as corpus:
            for line in corpus:
                try:
                    line = line.decode('gb18030')
                except:
                    print 'err'
                    continue
                line = line.lower()
                p = re.split('\t+', line.strip())
                if len(p) != 4: continue
                doc = p[0]
                title = p[1]
                bucket = p[2]
                image_count = p[3]
                doc_wordlist = self.doc2words( doc )
                title_wordlist = self.doc2words( title )
                doc_wordlist.update( title_wordlist )
                self.update_memory( doc_wordlist, bucket )
                i += 1
                print 'proc doc id                                  [%s]\r'%(i),
            print '\n', i, 'docs trained'
            corpus.close()
            self.dump_model()
    
    def construct_log_model(self):
        for k,v in self.C.iteritems():
            val = float(v)/float(self.N)
            self.log_C[k] = math.log(val)/self.LOG_BASE
        global_vcb_size = float( len( self.vcb ) + 1)
        for k,v in self.C2W.iteritems():
            if not k in self.log_C2W: self.log_C2W[k] = dict()
            for w,c in v.iteritems():
                val = float( c + 1 ) /( self.C[k] + global_vcb_size )
                self.log_C2W[k][w] = math.log( val ) / self.LOG_BASE
            val = 1.0/(global_vcb_size + self.C[k])
            self.log_base[k] = math.log( val ) / self.LOG_BASE
        for k,v in self.WDF.iteritems():
            self.IDF[k] = math.log( float( self.D )/ float(v) )

    def construct_log_model_only_entity(self):
        for k,v in self.C.iteritems():
            val = float(v)/float(self.N)
            self.log_C[k] = math.log(val)/self.LOG_BASE
        global_vcb_size = float( len( self.entity ) + 1)
        for k,v in self.C2W.iteritems():
            if not k in self.log_C2W: self.log_C2W[k] = dict()
            for w, c in v.iteritems():
                val = float( c + 1 ) /( self.C[k] + global_vcb_size )
                self.log_C2W[k][w] = math.log( val ) / self.LOG_BASE
            val = 1.0/( global_vcb_size + self.C[k] )
            self.log_base[k] = math.log( val ) / self.LOG_BASE
        for k,v in self.WDF.iteritems():
            self.IDF[k] = math.log( float( self.D )/ float(v) )

    def update_memory( self, words, bucket ):
        bucket = bucket.replace(u'"', '')
        bucket = bucket.replace(u',', ' ')
        most_possible_class = dict()
        for b in re.split(u'\s+', bucket.strip()):
            c = ''
            if b.find(u'.') != -1: c = b.strip().split(u'.')[0]
            else: c = b.strip()
            if c in most_possible_class: most_possible_class[c] += 1
            else: most_possible_class[c] = 1
        for k,v in sorted(most_possible_class.iteritems(),key=lambda(k,v):(v,k),reverse=True):
            most_possible_class = k
            break
        if most_possible_class == u"头条": return
        doc_words_count = sum( words.values() )
        self.N += doc_words_count
        self.D += 1
        if not most_possible_class in self.C: self.C[most_possible_class] = 0
        self.C[most_possible_class] += doc_words_count
        for k, v in words.iteritems():
            if not k in self.WDF: self.WDF[k] = 1
            else: self.WDF[k] += 1
            if not k in self.WTF: self.WTF[k] = v
            else: self.WTF[k] += v
            if not most_possible_class in self.C2W: self.C2W[most_possible_class] = dict()
            if not k in self.C2W[most_possible_class]: self.C2W[most_possible_class][k] = 0
            self.C2W[most_possible_class][k] += v

    def dump_model( self ):
        with codecs.open(self.pathinfo['class_doc_distribute'], 'w', 'gb18030') as model_C:
            for k,v in self.C.iteritems():
                model_C.write("%s\t%s\n"%(k,v))
            model_C.close()
        with codecs.open(self.pathinfo['word_class_distribute'], 'w', 'gb18030') as model_W:
            for k,v in self.C2W.iteritems():
                for w,c in v.iteritems():
                    model_W.write( '%s\t%s\t%s\n'%(k,w,c) )
            model_W.close()
        with codecs.open(self.pathinfo['doc_word_num'], 'w', 'gb18030') as model_N:
            model_N.write('%s'%(self.N))
            model_N.close()
        with codecs.open(self.pathinfo['doc_num'], 'w', 'gb18030') as model_D:
            model_D.write('%s'%(self.D))
            model_D.close()
        with codecs.open(self.pathinfo['word_tf'], 'w', 'gb18030') as model_WTF:
            for k,v in self.WTF.iteritems():
                model_WTF.write("%s\t%s\n"%(k,v))
            model_WTF.close()
        with codecs.open(self.pathinfo['word_df'], 'w', 'gb18030') as model_WDF:
            for k,v in self.WDF.iteritems():
                model_WDF.write("%s\t%s\n"%(k,v))
            model_WDF.close()

    def load_model( self ):
        with codecs.open(self.pathinfo['class_doc_distribute'], 'r', 'gb18030') as model_C:
            for l in model_C:
                p = re.split('\t', l.strip())
                if len(p)!=2: continue
                k = p[0]
                v = int(p[1])
                self.C[k] = v
            model_C.close()
        with codecs.open(self.pathinfo['word_tf'], 'r', 'gb18030') as model_WTF:
            for l in model_WTF:
                p = re.split('\t', l.strip())
                if len(p)!=2: continue
                k = p[0]
                v = int(p[1])
                self.WTF[k] = v
            model_WTF.close()
        with codecs.open(self.pathinfo['word_df'], 'r', 'gb18030') as model_WDF:
            for l in model_WDF:
                p = re.split('\t', l.strip())
                if len(p)!=2: continue
                k = p[0]
                v = int(p[1])
                self.WDF[k] = v
            model_WDF.close()
        with codecs.open(self.pathinfo['word_class_distribute'], 'r', 'gb18030') as model_W:
            for l in model_W:
                p = re.split('\t', l.strip())
                if len(p) != 3: continue
                k = p[0]
                w = p[1]
                c = int(p[2])
                if not k in self.C2W: self.C2W[k] = dict()
                self.C2W[k][w] = c
            model_W.close()
        with codecs.open(self.pathinfo['doc_num'], 'r', 'gb18030') as model_D:
            for l in model_D:
                l = l.strip()
                if l!='':
                    self.D = int(l)
            model_D.close()
        with codecs.open(self.pathinfo['doc_word_num'], 'r', 'gb18030') as model_N:
            for l in model_N:
                l = l.strip()
                if l!='':
                    self.N = int(l)
            model_N.close()
        self.construct_log_model()
    
    def get_feature_words( self, words, allwords_count, max_feature_words=100 ):
        tfidf = dict()
        maxval = 0
        for k,v in words.iteritems():
            if len(k)<2: continue
            if not k in self.IDF: continue
            #if not k in self.entity: continue
            if k in self.noisy_words: continue
            if k in self.high_freq: continue
            tf = float(v)/allwords_count
            idf= self.IDF[k]
            tfidf[k] = tf*idf
            if tfidf[k]>maxval: maxval=tfidf[k]
        if maxval == 0: maxval = 1
        feature_words = dict()
        for k,v in sorted(tfidf.iteritems(), key=lambda(k,v):(v,k), reverse=True):
            print "keywords: %s\t%s"%(k.encode('gb18030'), v/maxval)
            feature_words[k] = v/maxval
            if len(feature_words) >= max_feature_words: break
        return feature_words

    def classify( self, doc, title ):
        words = self.doc2words( doc )
        words_in_title = self.doc2words( title )
        words_in_title = [ (k,v) for k,v in words_in_title.iteritems() ]
        words.update( words_in_title )
        doc_words_count = sum( words.values() )
        words = self.get_feature_words( words, doc_words_count )
        hits_count = 0
        score = dict()
        for k in self.log_C:
            #doc_class_prob = self.log_C[k]
            doc_class_prob = 0
            for w, p in words.iteritems():
                if w in self.log_C2W[k]: 
                    doc_class_prob += self.log_C2W[k][w] * p
                else: doc_class_prob += self.log_base[k] * p
            score[k] = doc_class_prob
        big_class = ''
        first_class = ''
        i = 0
        for k,v in sorted(score.iteritems(),key=lambda(k,v):(v,k)):
            i += 1
            if i > 10: break
            if not k in self.fixed_class: continue
            if first_class == '': first_class=k
            big_class = k
            cand = list()
            for w,v in sorted(words.iteritems(),key=lambda(k,v):(v,k),reverse=True):
                k = big_class + u'.' + w
                if k in self.ime_buckets: cand.append(k)
            if len(cand)>0: return big_class, cand
        if first_class == '': return '', list()
        return first_class, list()
