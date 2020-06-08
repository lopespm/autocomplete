import java.io.IOException;
import java.util.StringTokenizer;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.NullWritable;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.WritableComparable;
import org.apache.hadoop.io.WritableComparator;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;

import org.apache.avro.Schema;
import org.apache.avro.mapred.AvroKey;
import org.apache.avro.mapred.AvroValue;
import org.apache.avro.mapreduce.AvroJob;
import org.apache.avro.mapreduce.AvroKeyValueInputFormat;

import org.apache.hadoop.conf.Configured;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;
import org.apache.hadoop.util.GenericOptionsParser;

import org.apache.hadoop.mapreduce.lib.input.TextInputFormat;
import org.apache.hadoop.mapreduce.lib.output.TextOutputFormat;


public class PhrasesWithWeightOrdered extends Configured implements Tool{

  public static class PhraseMapper extends Mapper<AvroKey<CharSequence>, AvroValue<Long>, LongWritable, Text>{
    private LongWritable weight = new LongWritable();
    public void map(AvroKey<CharSequence> key, AvroValue<Long> value, Context context) throws IOException, InterruptedException {
      weight.set(value.datum());
      context.write(weight, new Text(key.datum().toString()));
    }
  }

  public static class WeightSumReducer extends Reducer<LongWritable, Text, LongWritable, Text> {
    public void reduce(LongWritable weight, Iterable<Text> phrases, Context context) throws IOException, InterruptedException {
      for (Text phrase : phrases) {
        context.write(weight, phrase);
      }
    }
  }

  public static class DescendingKey extends WritableComparator {
    protected DescendingKey() {
        super(LongWritable.class, true);
    }

    //@SuppressWarnings("rawtypes")
    @Override
    public int compare(WritableComparable w1, WritableComparable w2) {
        LongWritable key1 = (LongWritable) w1;
        LongWritable key2 = (LongWritable) w2;          
        return -1 * key1.compareTo(key2);
    }
  }

  public static void main(String[] args) throws Exception {
    int result = ToolRunner.run(new Configuration(), new PhrasesWithWeightOrdered(), args);
    System.exit(result);
  }

  @Override
  public int run(String[] args) throws Exception {

    if (args.length != 3) {
      System.err.printf("Usage: %s [generic options] <input> <output> <unused>\n", getClass().getName());
      ToolRunner.printGenericCommandUsage(System.err);
      System.exit(2);
    }

    Path inPath = new Path(args[0]);
    Path outPath = new Path(args[1]);
    Integer baseWeight = Integer.valueOf(args[2]);
    
    Job job = Job.getInstance(getConf(), "Phrases With Weight Ordered");
    job.setJarByClass(PhrasesWithWeightOrdered.class);

    job.setInputFormatClass(AvroKeyValueInputFormat.class); 
    AvroJob.setInputKeySchema(job, Schema.create(Schema.Type.STRING));
    AvroJob.setInputValueSchema(job, Schema.create(Schema.Type.LONG));
    job.setOutputFormatClass(TextOutputFormat.class); 

    job.setMapperClass(PhraseMapper.class);
    job.setCombinerClass(WeightSumReducer.class);
    job.setReducerClass(WeightSumReducer.class);

    job.setSortComparatorClass(DescendingKey.class);

    job.setMapOutputKeyClass(LongWritable.class);
    job.setMapOutputValueClass(Text.class);

    job.setOutputKeyClass(LongWritable.class);
    job.setOutputValueClass(Text.class);

    job.setNumReduceTasks(1); // Make sure to output to a single file

    FileInputFormat.setInputPaths(job, inPath);
    FileOutputFormat.setOutputPath(job, outPath);
    
    return job.waitForCompletion(true) ? 0 : 1;
  }
}